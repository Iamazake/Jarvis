# Investigação: hang/timeout do processo Python e no_response (autopilot)

**Objetivo:** Descobrir por que `run_jarvis_message.py` às vezes não encerra (ou a API Node acusa timeout ~22s) mesmo quando a telemetria já mostra `jarvis_stop_end`. Separar **(1)** hang/timeout de processo (cleanup, threads, tasks) de **(2)** no_response (lógica retornando None).

**Restrições:** Zero implementação definitiva. Sugestões somente após provar causa com evidência. Entregar achados com arquivo + função + linha. Preservar cérebro (MCP/Python) e lógica reply/ignore.

---

## A) Achados no código (lista objetiva)

Cada item foi conferido no repositório. Tabela revisada com **linhas reais** e evidência.

### Trechos confirmados

| # | Arquivo | Função / trecho | Linhas | Evidência |
|---|---------|------------------|--------|-----------|
| A1 | jarvis/core/jarvis.py | start() | 66–67 | `asyncio.create_task(self._autonomy_loop())` — **não** guarda referência em atributo; não há `self._autonomy_task = ...`. |
| A2 | jarvis/core/jarvis.py | stop() | 72–82 | Apenas `self._running = False` e `await self.orchestrator.stop()`. **Não** cancela nenhuma task de autonomia; não há referência à task criada em start(). |
| A3 | jarvis/core/jarvis.py | _autonomy_loop() | 260–279 | `while self._running`: `await asyncio.sleep(60)` (L264), depois `await self.orchestrator.check_proactive()` (L270). Trata `CancelledError` com break (L275–276). |
| A4 | jarvis/core/orchestrator.py | start() | 53–54 | `asyncio.create_task(self._task_worker())` — **não** guarda referência; não há `self._worker_task = ...`. |
| A5 | jarvis/core/orchestrator.py | stop() | 58–68 | `self._running = False` e loop `for name, module in self.modules.items(): await module.stop()`. **Não** cancela a task do _task_worker. |
| A6 | jarvis/core/orchestrator.py | _task_worker() | 794–811 | `while self._running`: `task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)` (L798–800), depois `await self._execute_task(task)` (L804). Trata `CancelledError` (L808–809). |
| A7 | jarvis/core/orchestrator.py | check_proactive() | 753–782 | Itera `self._scheduled_tasks` (L763) e depois `for name, module in self.modules.items()` com `hasattr(module, 'check_proactive')` e `await module.check_proactive()` (L774–776). **Nota:** nenhum módulo em `modules/` implementa `check_proactive` atualmente (grep vazio); só o loop de _scheduled_tasks e a iteração vazia nos módulos. |
| A8 | jarvis/modules/calendar/reminder_scheduler.py | stop() | 94–102 | `self._running = False`, `self._task.cancel()`, `try: await self._task; except asyncio.CancelledError: pass`. **Comportamento correto** para shutdown. |
| A9 | jarvis/modules/voice/listener.py | stop() | 190–205 | `self._running = False`, fecha `_stream` e `_porcupine`. **Não** há `thread.join()` em nenhuma thread (ex.: se houver thread de captura de áudio). |
| A10 | jarvis/modules/voice/voice_module.py | stop() | 94–103 | `self._running = False`, `self._listening = False`, `self.listener.stop()`. **Não** faz join em threads. |
| A11 | jarvis/run_jarvis_message.py | main() | 115–125 | `response = asyncio.run(asyncio.wait_for(run(), timeout=...))` (L115); só **depois** de `asyncio.run()` retornar chama `output(...)` e `hard_exit(0)` (L116–124). Ou seja: `asyncio.run()` só retorna após o cleanup do event loop (cancelar e aguardar todas as tasks). |
| A12 | jarvis/run_jarvis_message.py | run() finally | 109–114 | `finally:` chama `log_timing('jarvis_stop_begin')`, `await jarvis.stop()`, `log_timing('jarvis_stop_end')`. Ou seja: **jarvis_stop_end** é impresso **antes** de `run()` retornar e **antes** do cleanup do `asyncio.run()` terminar. |
| A13 | jarvis/services/api/index.js | processPythonAI (spawn) | 111–172 | `spawn(pythonCmd, args, { cwd, env })` (L122); `python.stdout.on('data', ...)` (L140–142) e `python.stderr.on('data', ...)` (L144–146) acumulam em `stdout`/`stderr`. Timeout `setTimeout(..., timeoutMs)` com `timeoutMs = WEBHOOK_PROCESS_TIMEOUT_MS` (67: 22000). Ao estourar: `python.kill()`, `reject` com mensagem incluindo `extractTimingLines(stderr)`. Stdout e stderr **são drenados** pelos handlers. |
| A14 | jarvis/core/jarvis.py | process() | 195–217 | `result = await self.orchestrator.process(...)`; se tuple, `response, out_meta = result[0], result[1]`; depois `response = self._sanitize_whatsapp_response(response)` (L209); `return response` (L217). Se `result[0]` for None ou sanitize devolver None, **retorna None** → em run_jarvis_message gera `reason='no_response'`. |
| A15 | jarvis/core/orchestrator.py | _compose_message_via_ai / _route_to_module | 619–655, 716–739 | **_compose_message_via_ai:** retorna `None` se não há módulo ai ou sem `process` (L641); retorna `None` se `(text or "").strip()[:2000] or None` é vazio (L651); retorna `None` em exceção (L655). **_route_to_module:** se `module.process()` retorna tuple com primeiro elemento None, `response = result[0]` é None (L727); retorna `response, out_meta` (L739). Ou seja: módulo (ex.: ai) pode devolver `(None, out_meta)` e o pipeline sobe None até jarvis.process(). |

### Observação sobre A7

Nenhum arquivo em `jarvis/modules/` define `def check_proactive`. Portanto hoje o único trabalho em `check_proactive()` é o loop em `_scheduled_tasks` e a iteração sobre módulos (que não chama ninguém com implementação). Isso **reduz** a probabilidade de H2 no estado atual; porém, se no futuro algum módulo ganhar `check_proactive` com I/O lento, H2 volta a ser relevante.

---

## B) Hipóteses ordenadas por probabilidade

Para cada uma: **por quê** (1 frase) e **como provar**.

| Hipótese | Por quê | Como provar |
|----------|--------|--------------|
| **H1** – Tasks asyncio não canceladas (autonomy_loop / task_worker) | As tasks são criadas com `create_task` e nunca referenciadas nem canceladas em `stop()`; o `asyncio.run()` só retorna após cancelar e aguardar todas as tasks no cleanup; se essas tasks ainda estiverem vivas (ex.: em sleep(60) ou em check_proactive), o cleanup demora e o processo não termina a tempo. | Dump de `asyncio.all_tasks(loop)` no **final** de `jarvis.stop()` (após `await self.orchestrator.stop()`). Se aparecerem tasks com nome/coro de _autonomy_loop ou _task_worker ainda não `done`, H1 confirmada. Repetir dump no bloco `except TimeoutError` em main() se possível (stderr antes de hard_exit). |
| **H2** – check_proactive bloqueante/lento | O _autonomy_loop chama `await self.orchestrator.check_proactive()`. Se algum módulo tiver `check_proactive` e fizer I/O longo ou CPU sem ceder, a task demora a ser cancelada. | Hoje nenhum módulo implementa check_proactive; mesmo assim: log de tempo por “fase” em check_proactive (início; após _scheduled_tasks; antes/depois de cada módulo). Se no futuro algum módulo implementar, ver qual consome tempo. |
| **H3** – _task_worker preso em _execute_task | O worker chama `await self._execute_task(task)`; se esse caminho bloquear (I/O síncrono ou await sem timeout), o worker não reage ao cancelamento até terminar. | Log no início e no fim de `_execute_task`; em caso de timeout, o dump de tasks (C.1) pode mostrar a task do worker ainda em execução. |
| **H4** – Threads não-daemon (voz/áudio) | listener/voice_module não fazem join em threads; se houver thread de áudio viva (não-daemon), o processo Python não termina enquanto ela existir. | Dump de `threading.enumerate()` com nome, daemon e is_alive no final de run() ou no except TimeoutError. Threads não-daemon vivas indicam H4. |
| **H5** – Scheduler/background (ex.: APScheduler) | Nenhum uso de APScheduler foi encontrado; o calendar usa ReminderScheduler em asyncio com cancel no stop (A8). | Listar em orchestrator/jarvis quais módulos têm “scheduler” ou task de background; confirmar que todos são cancelados/aguardados no stop. C.4b. |
| **H6** – Buffer stdout/stderr | O Node já registra handlers para stdout e stderr (A13); `log_timing` usa flush=True. Risco de buffer cheio é baixo. | Confirmar no código do spawn que ambos os streams são sempre lidos; em cenário de muita saída, verificar se o processo não fica bloqueado em write. |
| **H7** – Subprocessos/recursos não fechados | tools_server ou outros podem abrir Popen/conexões; no run_jarvis_message o fluxo não inicia MCP explicitamente, mas módulos carregados podem abrir recursos que não são fechados no stop(). | Listar processos filhos (ex.: psutil) ou recursos abertos antes de sair; opcional. |

---

## C) Plano de instrumentação mínima (sem alterar comportamento)

Apenas pseudocódigo / mini-snippets de log; **não** implementar código completo.

### C.1. Dump de asyncio tasks ao final de jarvis.stop() e no TimeoutError do main()

- **Onde:** Final de `Jarvis.stop()`, após `await self.orchestrator.stop()`, antes do `logger.info` de “finalizado”. E, se possível, no bloco `except asyncio.TimeoutError` em `main()` (run_jarvis_message.py), antes de `hard_exit(0)` — nesse caso o dump deve ir para stderr (ex.: print com flush).
- **Pseudocódigo:**
  - Obter `loop = asyncio.get_running_loop()` (só dentro de contexto async).
  - `tasks = list(asyncio.all_tasks(loop))`.
  - Para cada task: logar `task.get_name()`, `task.done()`, e opcionalmente representação do coro (ex.: nome da coroutine).
  - Logar `len(tasks)`.
- **Exemplo de linha de log (conceitual):** `[DIAG] task name='Task-2' done=False coro=_autonomy_loop` e `[DIAG] total_tasks=3`.

### C.2. Dump de threads (threading.enumerate, daemon)

- **Onde:** No final de `run()` antes de retornar (ou no início do `except TimeoutError` em main(), antes de hard_exit), em run_jarvis_message.py.
- **Pseudocódigo:** `for th in threading.enumerate(): logar th.name, th.daemon, th.is_alive()`.
- **Exemplo:** `[DIAG] thread name='MainThread' daemon=False alive=True`.

### C.3. Logs de tempo por módulo em check_proactive()

- **Onde:** Em `orchestrator.check_proactive()`: um log no início; dentro do `for name, module in self.modules.items()`: log “begin” antes de `await module.check_proactive()` (se hasattr) e “end” depois, com timestamp ou elapsed.
- **Objetivo:** Ver se algum módulo (quando existir implementação) demora; hoje serve como baseline.

### C.4. Verificação de schedulers/timers vivos

- **Onde:** Em `orchestrator.stop()`: ao chamar `module.stop()` para cada módulo, logar quais têm atributo tipo “scheduler” ou “_task” (ex.: calendar ReminderScheduler). Confirmar que reminder_scheduler faz cancel + await no stop (já confirmado em A8).
- **Pseudocódigo:** Antes de `await module.stop()`, logar `getattr(module, '_task', None)` ou equivalente por módulo que se sabe ter scheduler.

### C.5. Checagem do spawn no Node (stdout/stderr drenados)

- **Onde:** `services/api/index.js`, função que faz spawn do Python (processPythonAI).
- **O que verificar:** Que `python.stdout.on('data', ...)` e `python.stderr.on('data', ...)` estão sempre registrados (já estão, A13) e que o processo não é encerrado (kill) sem dar tempo de consumir os streams. Nenhuma alteração necessária além de confirmar no código; opcionalmente documentar que ambos são drenados.

---

## D) Interpretação do sintoma jarvis_stop_end + timeout

### Mecânica

1. Dentro de `run()` (run_jarvis_message.py), o bloco `finally` executa na ordem: `log_timing('jarvis_stop_begin')`, `await jarvis.stop()`, `log_timing('jarvis_stop_end')`.
2. Quando aparece **jarvis_stop_end**, isso significa que `await jarvis.stop()` **já retornou**. Ou seja, a lógica de parada do Jarvis (e do orquestrador e módulos) terminou.
3. Em seguida `run()` retorna o valor (response) ao chamador. O chamador é `asyncio.run(asyncio.wait_for(run(), ...))`.
4. **asyncio.run()** só retorna **depois** de encerrar o event loop: cancelar todas as tasks agendadas e aguardar que terminem. Até lá, o processo Python continua vivo.
5. Se as tasks `_autonomy_loop` e `_task_worker` (ou outras) **não tiverem sido canceladas explicitamente** em `stop()`, elas ainda existem no loop. O asyncio as cancela no cleanup, mas:
   - se uma estiver em `await asyncio.sleep(60)`, ela só recebe o cancelamento no próximo ponto de await e então termina;
   - ou se estiver dentro de `await check_proactive()` (ou algo chamado por ele), só termina quando esse await retornar.
6. Enquanto o cleanup do asyncio.run() está aguardando essas tasks, o processo **não** chama `output()` nem `hard_exit(0)`. O Node não vê o processo fechar e, após 22s, dispara o timeout e mata o processo.

### Evidência esperada nos dumps (se essa hipótese for real)

- **Dump de tasks (C.1)** ao final de `jarvis.stop()`: deve mostrar uma ou mais tasks ainda **não** `done`, por exemplo com nome/coro associado a `_autonomy_loop` ou `_task_worker`. Isso indica que, ao terminar o stop(), essas tasks ainda estavam no loop e serão canceladas só no cleanup do asyncio.run(), atrasando a saída do processo.
- **Dump de threads (C.2)** no timeout: se houver threads não-daemon vivas (ex.: áudio), o processo também não encerra; isso seria evidência de H4 em vez de (ou além de) H1.

---

## E) Separar no_response

### Onde a pipeline pode retornar None

- **jarvis/core/jarvis.py** (L195–217): `response` vem de `orchestrator.process()` (primeiro elemento da tupla). Depois passa por `_sanitize_whatsapp_response(response)`. Se `response` já for None, `_sanitize_whatsapp_response` (L225–228) faz `if not response or not isinstance(response, str): return response` → retorna None. Então `jarvis.process()` retorna None.
- **jarvis/core/orchestrator.py**:
  - **process()** (L286–297): retorna `response, out_meta` vindos de `_route_to_module`. Se _route_to_module retornar (None, out_meta), o retorno é (None, out_meta).
  - **_route_to_module** (L717–739): se o módulo tem `process` e retorna tuple, `response = result[0]` (L727); se o módulo retornar (None, out_meta), response é None. Retorna `response, out_meta` (L739).
  - **_compose_message_via_ai** (L619–655): retorna None em três casos: (1) não há módulo ai ou não tem `process` (L641); (2) texto vazio após strip/trim (L651); (3) exceção (L655). _compose_message_via_ai é usada para “compor mensagem” em fluxos de envio; o retorno None da pipeline de **resposta** ao usuário vem do módulo (ex.: ai) em _route_to_module.
- Conclusão: **None** chega a `jarvis.process()` quando o orquestrador (ou o módulo roteado) devolve primeiro elemento None: seja por falha em _compose_message_via_ai, seja por módulo (ex.: ai) cujo `process()` retorna None ou (None, out_meta).

### Caminho que leva a ignore reason=no_response mesmo com autopilot enabled

- **run_jarvis_message.py** (L84–86): se `not autopilot_enabled`, emite `reason='not_in_autopilot'` e retorna None — esse não é no_response.
- **run_jarvis_message.py** (L116–124): quando `response is not None` → reply; quando `response is None` → `reason='no_response'`. Ou seja: **no_response** é quando o **autopilot está habilitado** (passou no check L84) mas o **retorno de `jarvis.process()` é None**. Isso ocorre quando a pipeline (orquestrador/módulo AI) não produz texto, por falha, por regra interna do módulo ou por caminho que retorna None (ex.: _compose_message_via_ai falhou ou módulo ai retornou None).

### Como instrumentar para descobrir “por que None” (sem alterar lógica)

1. **Em jarvis.process()** (core/jarvis.py): quando `response is None` (ou após sanitize ficar None), logar uma linha com: `response is None`, `type(result[0])` antes do sanitize, e chave relevante de `out_meta` (ex.: last_intent).
2. **No orquestrador**, no ponto onde se monta o retorno de `process()` (após _route_to_module): quando o primeiro elemento for None, logar intent, módulo usado (ou nome do módulo roteado) e, se disponível, um motivo (ex.: “module process returned None”).
3. **Em _route_to_module**: quando `response` (result[0] ou result) for None após chamar `module.process()`, logar `module_name`, `intent.type` e que o retorno do módulo foi None.
4. **Em _compose_message_via_ai**: nos branches que retornam None (L641, L651, L655), logar a razão (ex.: “no ai module”, “empty text”, “exception: …”). Assim se descobre se no_response vem de compose (fluxo de envio) ou do fluxo normal de resposta (módulo ai).

---

## F) Próximo passo recomendado (sem implementar)

1. **Aplicar instrumentação C.1 e C.2:** dump de tasks no final de `jarvis.stop()` (e, se possível, no except TimeoutError em main()); dump de threads no mesmo momento. Reproduzir o cenário que gera timeout 22s e coletar os logs.
2. **Interpretar dumps:** Se ao final de `jarvis.stop()` ainda houver tasks não `done` (ex.: _autonomy_loop, _task_worker), **H1 está confirmada**. Se houver threads não-daemon vivas, considerar **H4**.
3. **Opcional C.3 e C.4:** Se quiser baseline de check_proactive e schedulers, adicionar logs de tempo por etapa/módulo em check_proactive e listar schedulers/tasks em stop().
4. **Confirmar no Node (C.5):** Ler o trecho do spawn em index.js e documentar que stdout e stderr são drenados; sem mudança de código.
5. **Só então propor correção (alto nível):** Se H1 for a causa: guardar referências às tasks (_autonomy_loop e _task_worker) em start() e, em stop(), cancelar e aguardar essas tasks (com timeout de segurança, ex.: 2–5s). Opcionalmente, no caminho de sucesso de run_jarvis_message, chamar `hard_exit(0)` após output() para não depender do tempo de cleanup do asyncio.run(). **Não** implementar aqui; só após os logs confirmarem H1 (e eventualmente H4).

Para **no_response:** aplicar a instrumentação de E (logs em jarvis.process, orchestrator e _route_to_module / _compose_message_via_ai quando retorno for None) e reproduzir casos com reason=no_response para identificar o branch exato (módulo, intent, exceção ou texto vazio).
