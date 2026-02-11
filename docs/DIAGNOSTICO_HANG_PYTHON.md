# Diagnóstico: travamento / processo Python que não encerra

**Objetivo:** identificar por que o processo `run_jarvis_message.py` às vezes não finaliza (ou o Node acusa timeout) mesmo com telemetria mostrando `jarvis_stop_end`. Separar claramente **(1) hang/timeout do processo** e **(2) no_response (lógica não respondendo)**. **Nenhuma implementação** — só achados no código, hipóteses, plano de instrumentação mínima e próximos passos.

---

## A) Achados no código (lista objetiva)

| # | Arquivo | Função / trecho | Evidência |
|---|---------|------------------|-----------|
| A1 | `jarvis/core/jarvis.py` | `start()` linhas 66–67 | `asyncio.create_task(self._autonomy_loop())` — task criada e **nunca** guardada nem cancelada. |
| A2 | `jarvis/core/jarvis.py` | `stop()` linhas 72–81 | Apenas `_running = False` e `await self.orchestrator.stop()`; **não** há `_autonomy_task.cancel()` nem `await` da task. |
| A3 | `jarvis/core/jarvis.py` | `_autonomy_loop()` linhas 260–279 | Loop `while self._running` com `await asyncio.sleep(60)` e `await self.orchestrator.check_proactive()`; ao cancelar, só sai no próximo `await`; se estiver em `check_proactive()` pode demorar. |
| A4 | `jarvis/core/orchestrator.py` | `start()` linhas 53–54 | `asyncio.create_task(self._task_worker())` — task criada e **nunca** guardada nem cancelada. |
| A5 | `jarvis/core/orchestrator.py` | `stop()` linhas 58–68 | Apenas `_running = False` e `await module.stop()` por módulo; **não** há cancelamento de `_task_worker`. |
| A6 | `jarvis/core/orchestrator.py` | `_task_worker()` linhas 794–811 | `while self._running` com `await asyncio.wait_for(self._task_queue.get(), timeout=1.0)` e `await self._execute_task(task)`; cancelamento tende a ser rápido, mas se `_execute_task` bloquear, trava. |
| A7 | `jarvis/core/orchestrator.py` | `check_proactive()` linhas 753–782 | Itera `_scheduled_tasks` e depois todos os módulos com `hasattr(module, 'check_proactive')`; nenhum módulo em `modules/` implementa `check_proactive` (grep vazio), então só o loop de agendados; se um módulo futuro fizer I/O pesado aqui, segura a task. |
| A8 | `jarvis/modules/calendar/reminder_scheduler.py` | `start()` / `stop()` 85–102 | Faz `_task.cancel()` e `await self._task` no `stop()` — **correto**; não é fonte de hang. |
| A9 | `jarvis/modules/voice/listener.py` | `stop()` 190–205 | Apenas `_running = False`, fecha stream e porcupine; **não** há `thread.join()`; se houver thread de áudio ativa (ex. em `listen()` ou leitura contínua), processo pode não encerrar. |
| A10 | `jarvis/modules/voice/voice_module.py` | `stop()` 94–102 | Chama `self.listener.stop()`; não faz join em threads. |
| A11 | `jarvis/run_jarvis_message.py` | `main()` 116–126 | Caminho de sucesso: `response = asyncio.run(asyncio.wait_for(run(), ...))`; **só depois** de `asyncio.run()` retornar chama `output()` e `hard_exit(0)`. Ou seja: `asyncio.run()` só retorna após **cleanup do event loop** (cancelar e aguardar todas as tasks). Se _autonomy_loop ou _task_worker demorarem a encerrar, o processo fica preso **dentro** de `asyncio.run()` e o Node vê timeout. |
| A12 | `jarvis/run_jarvis_message.py` | `run()` 111–114 | `finally` chama `await jarvis.stop()` e em seguida `log_timing('jarvis_stop_end')`. Isso ocorre **antes** de `run()` retornar. Ou seja: quando você vê `jarvis_stop_end`, o `stop()` já terminou; o que ainda não terminou é o **cleanup** do `asyncio.run()` (cancelar tasks pendentes). |
| A13 | `jarvis/services/api/index.js` | `processPythonAI` 121–146 | `spawn` com handlers em `python.stdout.on('data')` e `python.stderr.on('data')` — ambos drenam em buffers em memória; **não** há risco óbvio de pipe cheio se o processo escreve com moderação. Timeout do Node (22s) mata o processo com `python.kill()`; o erro inclui `extractTimingLines(stderr)`. |
| A14 | `jarvis/core/jarvis.py` | `process()` 194–216 | Se `orchestrator.process()` retornar `(None, out_meta)` ou resposta vazia que vire None após sanitize, `return response` devolve None → em `run_jarvis_message` gera `reason='no_response'`. |
| A15 | `jarvis/core/orchestrator.py` | `_route_to_module` 713–716 | Se `module` for None, retorna `"Desculpe, não consigo processar..."` (string). O primeiro elemento da tupla só é None se o **módulo** (ex. ai) retornar None ou string vazia em algum caminho; ver `_compose_message_via_ai` (641, 652, 655) que retorna `None` em falha. |

---

## B) Hipóteses ordenadas por probabilidade (com porquê)

1. **H1 – Tasks asyncio não canceladas no stop() (muito provável)**  
   **Porquê:** Duas tasks são criadas com `create_task` e nunca referenciadas nem canceladas: `_autonomy_loop` (jarvis.py:67) e `_task_worker` (orchestrator.py:54). O `asyncio.run()` só retorna após cancelar e aguardar todas as tasks no cleanup; se uma delas estiver em `sleep(60)` ou em `check_proactive()`, o encerramento atrasa ou parece hang.

2. **H2 – check_proactive() lento ou bloqueante (provável)**  
   **Porquê:** A task do _autonomy_loop chama `await self.orchestrator.check_proactive()` (jarvis.py:271). Se um módulo tiver `check_proactive` e fizer I/O longo ou CPU sem ceder, a task demora a receber o cancelamento e o cleanup do event loop atrasa.

3. **H3 – _task_worker preso em _execute_task (média)**  
   **Porquê:** O worker (orchestrator.py:794–811) em loop chama `_execute_task(task)`; se esse caminho fizer chamada bloqueante ou I/O sem timeout, o worker não reage ao cancelamento até esse await terminar.

4. **H4 – Threads não-daemon (voz/áudio) (média)**  
   **Porquê:** voice_module e listener (listener.py:190–205) não fazem join em threads; se alguma thread de áudio estiver viva, o processo Python não termina enquanto a thread existir.

5. **H5 – APScheduler / BackgroundScheduler (baixa)**  
   **Porquê:** Nenhum uso de APScheduler foi encontrado no repo; o calendar usa ReminderScheduler com asyncio e cancel correto no stop(). Pode ser descartado a menos que alguma dependência indireta registre scheduler.

6. **H6 – Pipe stdout/stderr (baixa)**  
   **Porquê:** O Node (api/index.js) registra `stdout.on('data')` e `stderr.on('data')`; ambos são drenados. `log_timing` usa `flush=True`. Risco baixo; só checar se em pico de logs o buffer não enche.

7. **H7 – Subprocessos / recursos não fechados (baixa)**  
   **Porquê:** tools_server usa Popen; no run_jarvis_message o MCP não é iniciado pelo script diretamente. Possível se algum módulo carregado abrir processo ou conexão que não é fechada no stop().

**Priorização por ROI:** Primeiro provar H1 (dump de tasks), depois H2 (check_proactive), depois H4 (threads). Correção mais provável: guardar referências a _autonomy_loop e _task_worker e cancelá-las/aguardá-las em stop(); se necessário, hard_exit(0) no caminho de sucesso. Só depois avaliar processo Python persistente (daemon) como alternativa — recomendação, não implementar agora.

---

### Detalhe das hipóteses (referência)

### H1. Tasks asyncio criadas e nunca canceladas no `stop()` (muito provável)

**Onde:** [core/jarvis.py](jarvis/core/jarvis.py) e [core/orchestrator.py](jarvis/core/orchestrator.py).

- `jarvis.start()` faz `asyncio.create_task(self._autonomy_loop())` (linha 68). Em `jarvis.stop()` **não há** cancelamento dessa task; só `_running = False` e `await self.orchestrator.stop()`.
- `orchestrator.start()` faz `asyncio.create_task(self._task_worker())` (linha 54). Em `orchestrator.stop()` **não há** cancelamento dessa task.

**Por que trava:** ao retornar de `run()` (e imprimir `jarvis_stop_end`), o `asyncio.run()` entra na fase de cleanup e cancela todas as tasks. Até lá:
- `_autonomy_loop` pode estar em `await asyncio.sleep(60)` (até 60 s para acordar e ver `_running` False) ou dentro de `await self.orchestrator.check_proactive()`.
- Se estiver em `check_proactive()`, o cancelamento só é aplicado no próximo `await`. Se algum `module.check_proactive()` fizer I/O longo ou bloquear sem ceder, a task demora a encerrar e o processo “não volta”.

**Evidência no código:** não existe `_autonomy_task.cancel()` em `jarvis.stop()` nem `_task_worker` cancelado em `orchestrator.stop()`.

---

### H2. `check_proactive()` em algum módulo lento ou bloqueante (provável)

**Onde:** [core/orchestrator.py](jarvis/core/orchestrator.py) ~753–782 e módulos que implementam `check_proactive`.

- O loop de autonomia chama `await self.orchestrator.check_proactive()`, que percorre `self._scheduled_tasks` e todos os módulos com `check_proactive` (ex.: calendar, memory, etc.).
- Se algum módulo fizer rede, disco ou CPU pesado sem timeout (ou sem `await` que ceda ao cancelamento), a task do `_autonomy_loop` fica presa ali; o cleanup do `asyncio.run()` espera essa task e o processo demora a sair.

**Arquivos a inspecionar:** qualquer módulo em `modules/` que defina `check_proactive` (calendar, memory, etc.).

---

### H3. `_task_worker` preso em `_task_queue.get()` ou em `_execute_task` (média)

**Onde:** [core/orchestrator.py](jarvis/core/orchestrator.py) ~794–812.

- O worker faz `await asyncio.wait_for(self._task_queue.get(), timeout=1.0)` em loop. Ao cancelar, tende a sair rápido.
- Risco: se `_execute_task(task)` for chamado e uma tarefa encadeada não responder ao cancelamento (por exemplo, chamada síncrona bloqueante ou I/O sem timeout), o worker pode demorar a encerrar.

**Onde olhar:** corpo de `_execute_task` e qualquer código chamado por ele.

---

### H4. Módulo de voz (listener) com thread não-daemon (média)

**Onde:** [modules/voice/listener.py](jarvis/modules/voice/listener.py) e [modules/voice/voice_module.py](jarvis/modules/voice/voice_module.py).

- `AudioListener` usa `threading` e filas; em `voice_module.stop()` só se chama `listener.stop()` (seta `_running = False` e fecha stream). Não há `thread.join()` com timeout.
- Se alguma thread de áudio ficar em loop ou bloqueada em I/O (mic, PyAudio, etc.), o processo Python não termina enquanto essa thread existir.

**Evidência:** `listener.stop()` não faz join nas threads; `__del__` chama `stop()` mas não garante que as threads tenham acabado.

---

### H5. ReminderScheduler / calendar já param a task, mas ordem de shutdown pode travar (baixa)

**Onde:** [modules/calendar/reminder_scheduler.py](jarvis/modules/calendar/reminder_scheduler.py) ~94–102.

- O scheduler faz `self._task.cancel()` e `await self._task` no `stop()`, o que está correto.
- Se `orchestrator.stop()` chamar `module.stop()` em ordem que deixe outra task (ex.: autonomia) ainda rodando e dependendo do calendar, teoricamente pode haver condição de corrida; menos provável que H1/H2.

---

### H6. Stdout/stderr e deadlock com o Node (baixa, mas possível)

**Cenário:** o Node lê stdout do processo Python; o script imprime bastante em stderr (timing). Se o buffer do pipe encher e o Node não drenar stderr (ou só ler stdout), o processo Python pode bloquear em `print(..., file=sys.stderr)` e nunca chegar a `output()` / `hard_exit()`.

**Mitigação já presente:** `log_timing` usa `flush=True`. Mesmo assim, em cenários de muita saída ou leitura seletiva no Node, vale incluir no checklist (ex.: redirecionar stderr ou garantir que o Node leia ambos os streams).

---

### H7. Subprocessos ou recursos não fechados (baixa)

**Onde:** [mcp_servers/tools_server.py](jarvis/mcp_servers/tools_server.py) ~568–572 usa `subprocess.Popen`; outros módulos podem abrir processos ou conexões.

- No fluxo `run_jarvis_message.py` o MCP é usado indiretamente só se o módulo de IA carregar `JarvisAI` com `mcp_client` (no CLI sim; no run_jarvis_message a carga é via orchestrator/modules, sem criar `create_mcp_client` explícito no script). Mesmo assim, se algum módulo carregado iniciar subprocesso ou cliente HTTP/DB sem shutdown explícito, o processo pode esperar ou travar ao fechar.

---

### H8. `response is None` e `reason=no_response` (comportamento, não hang)

**Onde:** [run_jarvis_message.py](jarvis/run_jarvis_message.py) ~118–124.

- Se `jarvis.process()` retornar `None` (ex.: pipeline não definiu resposta, ou exceção tratada que retorna None), o script emite `action: 'ignore', reason: 'no_response'` e chama `hard_exit(0)`. Isso é saída limpa, não travamento.
- Se “às vezes retorna rápido com no_response”, a causa é de lógica/negócio (orchestrator/IA não produzindo texto), não de processo que não encerra.

---

### H9. Event loop com muitas tasks ou callbacks atrasando o cleanup (baixa)

- Se houver muitas tasks pendentes ou callbacks agendados, o `asyncio.run()` pode demorar a cancelar e aguardar todas. Isso tende a ser efeito, não causa raiz; a causa costuma ser uma ou poucas tasks que não reagem ao cancelamento (H1/H2/H3).

---

### H10. `hard_exit(0)` não usado no caminho “sucesso” antes do cleanup do `asyncio.run()` (confirmado)

**Onde:** [run_jarvis_message.py](jarvis/run_jarvis_message.py) ~116–126.

- No caminho de sucesso fazemos `output(...)` e **só depois** `hard_exit(0)`. Para chegar aí, é necessário que `asyncio.run(run())` retorne. O `asyncio.run()` só retorna depois de encerrar o event loop, o que inclui cancelar e aguardar as tasks (ex.: _autonomy_loop, _task_worker). Ou seja: o processo **nunca** usa `hard_exit` no fluxo feliz antes de passar pelo cleanup; se o cleanup demora, o timeout do Node pode estourar mesmo com “jarvis_stop_end” já impresso.

**Conclusão:** o travamento que você vê (timeout 22 s com timing até jarvis_stop_end) é consistente com cleanup do asyncio lento por causa de tasks não canceladas explicitamente (H1) e/ou uma delas presa em `check_proactive()` ou equivalente (H2).

---

## C) Como provar rápido (instrumentação mínima)

Fazer **em ordem**; não alterar comportamento de produção, só adicionar logs/dumps.

### C.1. Dump de tasks asyncio ao sair de `jarvis.stop()` e no timeout

- **Onde:** no final de `Jarvis.stop()`, após `await self.orchestrator.stop()`; e no `except TimeoutError` em `main()` (stderr) antes de `hard_exit(0)`.
- **Pseudocódigo (Jarvis.stop() e no except TimeoutError):**
  - Obter `loop = asyncio.get_running_loop()`, `tasks = list(asyncio.all_tasks(loop))`.
  - Para cada task: `print(f"[DIAG] task name={t.get_name()!r} done={t.done()}", file=sys.stderr, flush=True)`.
  - `print(f"[DIAG] total_tasks={len(tasks)}", file=sys.stderr, flush=True)`.
- **Objetivo:** ver quais tasks ainda existem quando “stop” terminou (ex.: _autonomy_loop, _task_worker) e se há outras inesperadas.

### C.2. Dump de threads (threading.enumerate, daemon)

- **Onde:** no final de `run()` antes de retornar e/ou no bloco `except TimeoutError` antes de `hard_exit(0)`.
- **Pseudocódigo:**
```python
import threading
for th in threading.enumerate():
    print(f"[DIAG] thread name={th.name!r} daemon={th.daemon} alive={th.is_alive()}", file=sys.stderr, flush=True)
```
- **Objetivo:** ver threads não-daemon (H4).

### C.3. Detectar subprocessos vivos

- **Onde:** mesmo ponto do 2.2 (antes de sair ou no timeout).
- **O que:** em Windows, não depender de `psutil` se não estiver disponível; opcionalmente `subprocess` listando filhos se houver API (em Python puro é limitado). Se aceitar dependência, `psutil.Process().children()`.
- **Objetivo:** descartar processos filhos presos (ex.: ferramentas que abrem browser/apps).

### C.4. Marcar início/fim de `check_proactive()` e tempo por módulo

- **Onde:** em `orchestrator.check_proactive()`: log no início; dentro do loop por módulo, log antes e depois de `await module.check_proactive()` com timestamp.
- **Pseudocódigo:** no início `print("[DIAG] check_proactive begin", ..., flush=True)`; no loop `print(f"[DIAG] check_proactive module={name} begin", ...)` antes do await e `... end"` depois; no fim `print("[DIAG] check_proactive end", ...)`.
- **Objetivo:** ver se algum módulo demora (H2).

### C.4b. Identificação de schedulers ativos e como param

- **Onde:** em `orchestrator.stop()` ao chamar `module.stop()` por módulo; e em módulos como calendar (ReminderScheduler).
- **O que:** logar quais módulos têm scheduler (ex.: `hasattr(module, '_task')` ou `_scheduled_tasks`) e que `stop()` foi chamado; confirmar que ReminderScheduler faz `_task.cancel()` e `await self._task`. Objetivo: descartar scheduler mantendo processo vivo.

### C.5. (Teste de correção) Guardar referência às tasks e cancelar no stop

- **Objetivo:** testar a hipótese H1 sem mudar ainda a arquitetura.
- **Onde:**  
  - Em `jarvis.start()`: guardar `self._autonomy_task = asyncio.create_task(self._autonomy_loop())`.  
  - Em `jarvis.stop()`: antes de `await self.orchestrator.stop()`, fazer `if getattr(self, '_autonomy_task', None): self._autonomy_task.cancel(); try: await self._autonomy_task; except asyncio.CancelledError: pass`.  
  - Em `orchestrator.start()`: guardar `self._worker_task = asyncio.create_task(self._task_worker())`.  
  - Em `orchestrator.stop()`: no início, `if getattr(self, '_worker_task', None): self._worker_task.cancel(); try: await self._worker_task; except asyncio.CancelledError: pass`.
- **Medir:** se o timeout de 22 s deixa de ocorrer ou diminui muito, H1 está confirmada.

### C.6. Timeout interno no loop de autonomia (opcional)

- **Onde:** em `_autonomy_loop`, envolver `await self.orchestrator.check_proactive()` em `asyncio.wait_for(..., timeout=10.0)`.
- **Objetivo:** evitar que um único `check_proactive()` segure o processo por tempo indefinido; logar se der timeout.

### C.7. Garantir que o Node drene stdout e stderr

- **Onde:** no spawn do Node (API), verificar se stderr é lido (ou se está sendo consumido em algum buffer). Se quiser, no script Python: em modo “debug”, escrever timings em arquivo em vez de stderr, para descartar H6. Em `services/api/index.js` confirmar que stdout e stderr são ambos drenados.

---

## D) Interpretação dos logs atuais (jarvis_stop_end antes do timeout)

- **O que significa:** Quando a telemetria mostra `jarvis_stop_end` (e até `jarvis_process_end` em &lt;15s) mas o Node ainda acusa timeout 22000ms: o `finally` de `run()` já executou `await jarvis.stop()` e `log_timing('jarvis_stop_end')`, mas em seguida `run()` retorna para `asyncio.run(...)`. O `asyncio.run()` só retorna depois de encerrar o event loop (cancelar e aguardar todas as tasks). Se _autonomy_loop ou _task_worker demorarem a reagir ao cancelamento, o cleanup fica esperando e o processo não termina — o Node dispara o timeout.
- **Conclusão:** `jarvis_stop_end` indica que a lógica de stop do Jarvis terminou; o “travamento” ocorre **depois**, no cleanup do `asyncio.run()`. Correção mais provável: cancelar explicitamente as tasks em `stop()` e, se necessário, `hard_exit(0)` no caminho de sucesso.

---

## E) Próximo passo recomendado (sem implementar ainda)

1. Aplicar instrumentação C.1, C.2, C.4 (dump de tasks no fim de `jarvis.stop()`, dump de threads, marcar check_proactive por módulo); reproduzir o timeout e coletar logs.
2. Validar H1: se no dump aparecerem tasks como _autonomy_loop ou _task_worker ainda não done ao final do stop, H1 confirmada. Testar a correção C.5 (guardar referências e cancelar no stop) em branch; se o timeout sumir, adotar.
3. Se H2 relevante: logs de C.4 mostram qual módulo demora; considerar C.6 (timeout em check_proactive).
4. Se H4: threads não-daemon no dump; garantir join com timeout no stop do módulo.
5. Não implementar daemon persistente (B) ou pool (C) até shutdown determinístico (A) estável.

---

## Separar “no_response” (lógica que não responde)

- **Onde `jarvis.process` retorna None:** Em `core/jarvis.py` ~194–216, `response` vem do primeiro elemento de `orchestrator.process()`. Se for None (ou virar None após sanitize), em `run_jarvis_message.py` L118–124 emite `action: 'ignore', reason: 'no_response'`.
- **Onde o orquestrador devolve None:** Em `orchestrator.py`, `_compose_message_via_ai` retorna `None` em falha (~641, 652, 655); se o módulo (ex.: ai) retornar None, o retorno sobe e vira no_response.
- **Regra que gera ignore com autopilot:** no_response não é “autopilot desligado”; é ausência de resposta (None) do pipeline (IA/orquestrador/módulo). Autopilot pode estar enabled e a IA ou roteamento não produzir texto.
- **Instrumentar sem alterar lógica:** (1) Em `jarvis.process()` quando `response is None`, logar `(response, type(response), out_meta)`. (2) No orquestrador, ao montar retorno None, logar intent, módulo e motivo. (3) Em `_compose_message_via_ai` nos branches que retornam None, logar a razão. Assim descobre-se o caminho que gera no_response.

---

## 3. Propostas de solução (sem codar ainda), ordenadas por ROI

### A) Shutdown determinístico mantendo spawn por mensagem (maior ROI)

- **Ideia:** manter um processo Python por mensagem (como hoje), mas garantir que todas as tasks e recursos encerrem de forma determinística antes do script terminar.
- **Ações típicas:**  
  - Guardar referências a `_autonomy_loop` e `_task_worker`; em `jarvis.stop()` e `orchestrator.stop()` cancelar e aguardar essas tasks com timeout (ex.: 2–5 s).  
  - Garantir que módulos (voz, calendar, etc.) em `stop()` cancelem tasks, façam join em threads com timeout e fechem recursos.  
  - No script, após `asyncio.run(run())`, chamar `hard_exit(0)` no caminho de sucesso para não depender do cleanup lento do run() (ou garantir que o cleanup seja rápido).
- **Prós:** mudança localizada, sem nova infra; MCP e cérebro intactos; idempotência e decisão reply/ignore continuam no Python.  
- **Contras:** ainda há custo de startup por mensagem (imports, carga de módulos).  
- **Risco:** baixo. **Esforço:** baixo/médio.  
- **Idempotência:** inalterada (message_id no Node + dedupe no Python se houver).

---

### B) Processo Python persistente (serviço local ou “worker” único)

- **Ideia:** um único processo Python rodando como serviço (ou um worker que escuta fila local/socket). O Node envia a mensagem (ex.: via HTTP ou fila) e recebe a resposta; não spawna novo processo por mensagem.
- **Prós:** sem startup por mensagem; event loop e MCP podem ficar sempre ativos; shutdown só em reinício do serviço.  
- **Contras:** nova peça (serviço Python), deploy e monitoramento; necessidade de protocolo (HTTP/gRPC/fila) e tratamento de falhas/reconexão.  
- **Risco:** médio. **Esforço:** alto.  
- **Idempotência:** manter message_id no Node e, no serviço Python, dedupe por message_id (e opcionalmente in-flight) para não processar duas vezes.

---

### C) Pool de workers Python (N processos) com fila interna

- **Ideia:** N processos Python que consomem de uma fila (ex.: Redis, fila em disco, ou socket). O Node envia job para a fila; um worker pega, processa e devolve a resposta (outra fila ou callback HTTP).
- **Prós:** escalabilidade e isolamento (um worker travado não derruba os outros).  
- **Contras:** mais complexidade (fila, retry, dead letter, timeouts), deploy e operação.  
- **Risco:** médio. **Esforço:** alto.  
- **Idempotência:** no Node (message_id) e nos workers (dedupe por message_id ao consumir).

---

Recomendação prática: **implementar A primeiro** (cancelamento explícito das tasks + shutdown ordenado + `hard_exit` no sucesso se necessário). Se ainda houver intermitência, aprofundar em H2/H4 (check_proactive e threads) e só então avaliar B ou C.

---

## 4. Arquivos e trechos para inspecionar primeiro

| Prioridade | Arquivo | Trecho / o que ver |
|------------|--------|---------------------|
| 1 | [jarvis/run_jarvis_message.py](jarvis/run_jarvis_message.py) | `main()`, `run()`, uso de `asyncio.run()` e `hard_exit`; onde o fluxo pode não chegar a `output()` / `hard_exit`. |
| 2 | [jarvis/core/jarvis.py](jarvis/core/jarvis.py) | `start()` linha 67–68: `asyncio.create_task(self._autonomy_loop())`; `stop()` 72–81: ausência de cancelamento da task; `_autonomy_loop()` 260–279: `sleep(60)` e `check_proactive()`. |
| 3 | [jarvis/core/orchestrator.py](jarvis/core/orchestrator.py) | `start()` 54: `asyncio.create_task(self._task_worker())`; `stop()` 58–68: ausência de cancelamento do worker; `_task_worker()` 794–812: loop e `_task_queue.get()`; `check_proactive()` 753–782: iteração sobre módulos. |
| 4 | [jarvis/modules/calendar/reminder_scheduler.py](jarvis/modules/calendar/reminder_scheduler.py) | `start()` / `stop()` e `_scheduler_loop`: confirmação de cancelamento correto da task. |
| 5 | [jarvis/modules/voice/voice_module.py](jarvis/modules/voice/voice_module.py) | `start()` / `stop()` e uso de `listener`. [modules/voice/listener.py](jarvis/modules/voice/listener.py): threads (daemon ou não), como param e se há join. |
| 6 | Módulos com `check_proactive` | Buscar em `modules/` por `def check_proactive` e ver se há I/O ou CPU longo sem timeout. |
| 7 | [jarvis/core/mcp_client.py](jarvis/core/mcp_client.py) | Onde o MCP é iniciado no fluxo CLI vs run_jarvis_message (se no run_jarvis_message os módulos carregados iniciam algo em background). |
| 8 | [jarvis/mcp_servers/base.py](jarvis/mcp_servers/base.py) | `run_embedded()` e `stop()`: se criam threads ou tasks que precisam ser fechadas. |
| 9 | [jarvis/services/api/index.js](jarvis/services/api/index.js) | Trecho que faz spawn do Python: como stdout/stderr são lidos; se há risco de buffer cheio (H6). |

---

## 5. Checklist de investigação (ordem sugerida)

1. [ ] Adicionar em `jarvis.stop()` e `orchestrator.stop()` o cancelamento explícito das tasks de background (2.5) e medir se o timeout de 22 s desaparece ou cai muito.  
2. [ ] Logar `asyncio.all_tasks(loop)` ao final de `jarvis.stop()` (2.1).  
3. [ ] Logar `threading.enumerate()` antes de sair / no timeout (2.2).  
4. [ ] Adicionar logs de tempo em `check_proactive()` por módulo (2.4); rodar até reproduzir e ver qual módulo demora.  
5. [ ] Revisar `voice_module` e `listener` para threads não-daemon e falta de join (2.2 + H4).  
6. [ ] (Opcional) Timeout em `check_proactive()` (2.6) e checagem de stderr no Node (2.7).  
7. [ ] Se ainda travar: usar o dump de tasks (2.1) no momento do timeout (ex.: signal handler ou segundo processo que inspeciona o processo Python) para ver a task que não termina.

Com isso você consegue fechar o diagnóstico (H1/H2/H4) e decidir se basta a solução A ou se vale evoluir para B/C.
