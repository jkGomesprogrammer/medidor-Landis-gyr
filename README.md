# 📟 Comunicação com Medidor Saga 1000 (Protocolo ABNT NBR 14522)

> **⚠️ ATENÇÃO:**  
> Este código **não está finalizado** e apresenta erros de conexão devido a respostas incorretas que não conferem com os cálculos.  
> Portanto, **NÃO DEVE SER USADO EM PRODUÇÃO**.

# Comunicação TCP com Medidor via Gateway
Este script Python realiza comunicação TCP com um medidor usando protocolo ABNT, enviando comandos formatados com CRC e recebendo a resposta. As configurações de IP, porta e parâmetros do comando são carregadas de um arquivo .env.

# 📋 Descrição
    Este script Python realiza comunicação TCP com um medidor Saga 1000 via gateway, usando o protocolo ABNT NBR 14522. 
    Ele monta comandos com CRC conforme o protocolo, envia via TCP e recebe as respostas, exibindo-as em formato hexadecimal.
    As configurações (IP do gateway, porta, endereço do medidor, código da função e flag de envio do ENQ) são carregadas a partir de um arquivo .env.


# 🚀 Requisitos
- Python 3.x
- Biblioteca python-dotenv para carregar variáveis de ambiente


# 💾 Instalação da dependência
``` bash
    pip install python-dotenv
```

# ⚙️ Configuração
Crie um arquivo .env na raiz do projeto com as variáveis:
``` bash
    GATEWAY_IP=
    GATEWAY_PORT=
    ENDERECO_LOGICO=1
    CODIGO_FUNCAO=1
    ENVIAR_ENQ=True
```
| Variável           | Descrição                                                                 |
|--------------------|---------------------------------------------------------------------------|
| `GATEWAY_IP`       | IP do gateway para conexão TCP                                            |
| `GATEWAY_PORT`     | Porta TCP do gateway                                                      |
| `ENDERECO_LOGICO`  | Endereço lógico do medidor                                                |
| `CODIGO_FUNCAO`    | Código da função a ser consultada                                         |
| `ENVIAR_ENQ`       | Se deve enviar caractere ENQ (0x05) antes do comando (`True` ou `False`)  |


# ▶️ Como usar
Execute o script com:
```bash
python medidorSaga1000.py
```
O script realiza:

- Conexão TCP com o gateway

- Envio opcional do caractere ENQ e espera pela resposta

- Montagem e envio do comando ABNT com CRC

- Recebimento e exibição da resposta do medidor em hexadecimal

## 📑 Documentação 
- [📄 Protocolo ABNT NBR 14522 (PDF)](docs/NormasAbntNbr14522.pdf)
- [📘 Manual do Medidor Saga 1000](docs/SAGA1000.pdf)
- [📘 Manual do Gatway BlackBox RS-232](docs/manualRS232.pdf)

# 🤝 Contribuindo
Contribuições são bem-vindas!

1. Faça um fork deste repositório

2. Crie uma branch para sua funcionalidade:
git checkout -b minha-nova-funcionalidade

3. Faça commit das suas alterações:
git commit -m "Descrição da nova funcionalidade"

4. Envie para sua branch remota:
git push origin minha-nova-funcionalidade

5. Abra um Pull Request neste repositório

# 📄 Licença
Este projeto é open-source e pode ser usado e modificado livremente para fins educacionais, de pesquisa ou integração com sistemas baseados em medidores Saga 1000.
