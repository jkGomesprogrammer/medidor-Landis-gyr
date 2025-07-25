# 📟 Comunicação com Medidor Saga 1000 (Protocolo ABNT NBR 14522)

> **⚠️ ATENÇÃO:**  
> Este código **não está finalizado** e apresenta erros de conexão devido a respostas incorretas que não conferem com os cálculos.  
> Portanto, **NÃO DEVE SER USADO EM PRODUÇÃO**.


**Este script realiza a comunicação com **medidores Saga 1000** via **TCP/IP e UDP**, utilizando o **protocolo ABNT NBR 14522**.**

### Ele permite:
- Ativar o medidor via UDP
- Enviar comandos de leitura via TCP
- Interpretar respostas
- Validar integridade dos dados via CRC
- Exibir resultados em ponto flutuante (float24 convertido para float32)

---

## ⚙️ Requisitos

- Python 3.6+
- Acesso à rede do medidor
- Endereço IP e porta TCP do medidor

---

## 🚀 Como usar

1. Execute o script:
```bash
    python medidorSaga1000.py
```

2. Siga o menu interativo:

```bash
    Digite o IP do medidor

    Informe a porta TCP (ex: 5000)

    Escolha o número do comando (ex: 14)

    Para comandos como o 14, forneça também o número de série
```

# O programa:

- Envia pacotes UDP de ativação

- Estabelece conexão TCP

- Envia o comando escolhido

- Aguarda e interpreta a resposta

# 📦 Estrutura do Protocolo
**Este script usa os seguintes símbolos do protocolo ABNT:**

```
| Byte        | Significado                    |
|-------------|--------------------------------|
| ENQ (0x05)  | Enquiry (solicitação de envio) |
| ACK (0x06)  | Acknowledge (confirmação)      |
| NAK (0x15)  | Negative ACK (erro)            |
| WAIT (0x10) | Medidor ocupado                |
| ALO (0xFF)  | Início de comunicação          |
```

# 📚 Principais Funções
- calcula_crc16(data: bytes)
    - Calcula o CRC-16 para garantir integridade da mensagem.

- complementar_bytes(data: bytes)
    - Inverte todos os bits de cada byte da mensagem — exigência do protocolo.

- montar_comando_generico(codigo: int, argumento: int = 0x00)
    - Monta uma mensagem genérica contendo:

            código do comando

            byte de comando fixo (0x63)

            argumento (default 0x00)

            CRC

            complementação de bytes

            prefixo ENQ

- montar_comando_14(numero_serie: int)
    - Monta o comando 14, enviando um número de série seguido de 60 bytes nulos e CRC.

- validar_crc_resposta(resposta: bytes)
    - Valida se o CRC da resposta do medidor bate com o CRC calculado localmente.

- float24_to_float32(b1, b2, b3)
    - Converte 3 bytes (Float24) recebidos do medidor em um float32 padrão.

- esperar_enq(sock, timeout=20)
    - Aguarda a chegada de um byte ENQ do medidor, sinalizando que ele está pronto.

- enviar_alo(sock)
    - Envia múltiplos bytes ALO (0xFF) para iniciar a comunicação TCP.

- enviar_pacote_udp_ativacao(ip_destino)
    - Envia um pacote UDP especial (0x020121c03803) para ativar o medidor antes da conexão TCP.

- enviar_comando(sock, mensagem)
    - Controla toda a lógica de envio e resposta:

            Envia ALO

            Aguarda ENQ

            Envia comando

            Trata WAIT, NAK, ACK

            Verifica CRC da resposta

            Reenvia comando se necessário

- interpretar_float24_em_bloco(resposta: bytes)
    - Varre a resposta recebida e tenta converter blocos de 3 bytes em valores float legíveis.

# 💡 Exemplo de uso (comando 14)
```bash
        Digite o IP do medidor (ou 'sair' para terminar): 192.168.0.101 '(EX)'

        Digite a porta TCP do medidor: 5000 '(EX)'

        Digite o número do comando (exemplo 14): 14 '(EX)'

        Digite o número de série do leitor: 0x010203 '(EX)'
        Resultado esperado:

        Ativação via UDP

        Conexão via TCP

        Comando enviado

        Resposta validada

        Float24 interpretado
```

## 📑 Documentação 
### [📄 Protocolo ABNT NBR 14522 (PDF)](docs/NormasAbntNbr14522.pdf)
### [📘 Manual do Medidor Saga 1000](docs/SAGA1000.pdf)
### [📘 Manual do Gatway BlackBox RS-232](docs/manualRS232.pdf)

# 🛠️ Contribuindo
### Contribuições são bem-vindas!

    Faça um fork

    Crie uma branch (git checkout -b nova-funcionalidade)

    Commit suas mudanças (git commit -m 'Adiciona nova funcionalidade')

    Push na branch (git push origin nova-funcionalidade)

    Crie um Pull Request

# 📄 Licença
### Este projeto é open-source e pode ser usado e modificado livremente para fins educacionais, de pesquisa ou integração com sistemas baseados em medidores Saga 1000.
