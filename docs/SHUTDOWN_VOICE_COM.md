# Shutdown: travamento por COM/comtypes (TTS no Windows)

## Causa (evidência faulthandler)

O processo Python não encerra após `jarvis_stop_end` porque:

- **MainThread** trava em `comtypes\client\_events.py` linha 107 em `__del__`.
- **asyncio_0** aparece no worker do `ThreadPoolExecutor` (usado por pyttsx3/run_in_executor).

O pyttsx3 (TTS offline no Windows) usa SAPI/COM. Ao encerrar o processo, os objetos COM são destruídos e o `__del__` do comtypes tenta desconectar eventos e pode bloquear, impedindo o `asyncio.run()` de finalizar.

## Onde no código

- **modules/voice/synthesizer.py:** `_init_pyttsx3()` chama `pyttsx3.init()` (via run_in_executor). O engine mantém referências COM; não havia `stop()` nem zeragem de `_engine` no shutdown.
- **modules/voice/voice_module.py:** Em `start()` era chamado `await self.synthesizer.initialize()`, criando o engine TTS mesmo quando o fluxo (ex.: run_jarvis_message) nunca fala.

## Correções aplicadas

1. **Synthesizer.stop()**  
   Chama `engine.stop()` se existir, depois `_engine = None`, `_elevenlabs_client = None`, `_initialized = False`. Reduz a chance de o destrutor COM rodar em contexto que trave.

2. **TTS lazy**  
   O TTS não é mais inicializado em `VoiceModule.start()`. Só é inicializado no primeiro `speak()`. No run_jarvis_message (sem fala), o engine pyttsx3 nunca é criado e o processo não entra no cleanup COM.

3. **VoiceModule.stop()**  
   Chama `synthesizer.stop()` antes de parar o listener, para liberar o engine explicitamente.

4. **JARVIS_DISABLE_VOICE=1**  
   - No **orchestrator:** o módulo `voice` não é carregado.  
   - No **VoiceModule:** se a variável estiver definida, `start()` não inicializa TTS/STT/Listener.  
   Teste A/B: rodar com `set JARVIS_DISABLE_VOICE=1` e confirmar que o processo encerra logo após `jarvis_stop_end`.

## Teste A/B

```bat
set JARVIS_DISABLE_VOICE=1
python run_jarvis_message.py --message "oi" --jid "5511...@s.whatsapp.net" --sender "Nome"
```

Sem voice, o processo deve terminar em poucos segundos e não travar. Com voice ativo (e TTS inicializado em algum fluxo que chame `speak()`), usar `synthesizer.stop()` no `voice_module.stop()` para mitigar.

## no_response (secundário)

O autopilot às vezes “sumia” porque o TTL do JID expirava e `get_autopilot` removia a entrada. Foi corrigido com `refresh_autopilot_ttl(jid)` ao receber mensagem. Para diagnosticar outros casos de `no_response`, use `JARVIS_DIAG=1` e verifique os logs em `jarvis.process()` e no orquestrador (`_compose_message_via_ai`, `_route_to_module`) quando a resposta for None.
