#medidorSaga1000.py

#Código para comunicação com medidores Saga 1000 via TCP/IP e UDP
#Baseado no protocolo ABNT NBR 14522
#Este código implementa a comunicação com medidores Saga 1000, incluindo envio de comandos e interpretação de respostas.
#Ele utiliza sockets para comunicação TCP e UDP, e inclui funcionalidades para enviar comandos, receber respostas,

import struct
import socket
import time

ENQ = 0x05   # Enquiry: sinaliza intenção de comunicação
ACK = 0x06   # Acknowledge: confirmação de recebimento
NAK = 0x15   # Negative Acknowledge: erro na recepção
WAIT = 0x10  # Dispositivo ocupado, espere
ALO = 0xFF   # “ALO” é um byte específico desse medidor para iniciar a comunicação

# Constantes para limites de retransmissões
MAX_NAKS = 7
MAX_WAITS = 12
MAX_RETRIES = 7
MAX_ALO = 5

# Função para calcular o código de verificação de 16 bits (CRC-16)
def calcula_crc16(data: bytes):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x8005) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

# Função para complementar os bytes (inverte os bits de cada byte)
def complementar_bytes(data: bytes) -> bytes:
    return bytes((~b) & 0xFF for b in data)

# Função que monta o pacote de comando completo para ser enviado ao medidor, seguindo o protocolo ABNT NBR 14522
def montar_comando_generico(codigo: int, argumento: int = 0x00):
    comando = 0x63
    dados_sem_crc = bytes([codigo, comando, argumento])
    crc = calcula_crc16(dados_sem_crc)
    crc_bytes = struct.pack('>H', crc)
    dados_completos = dados_sem_crc + crc_bytes
    dados_complementados = complementar_bytes(dados_completos)
    mensagem = bytes([ENQ]) + dados_complementados
    return mensagem

# Função exclusiva para o comando 14, comando padrão 
def montar_comando_14(numero_serie: int):
    dados = bytes([0x14]) + numero_serie.to_bytes(3, 'big') + bytes(60)
    crc = calcula_crc16(dados)
    crc_bytes = struct.pack('>H', crc)
    dados_completos = dados + crc_bytes
    dados_complementados = complementar_bytes(dados_completos)
    return dados_complementados

# Função que valida o CRC-16 (Código de redundância cíclica) da resposta recebida do medidor, garatindo que os dados não foram corrompidos durante a transmissão
def validar_crc_resposta(resposta: bytes):
    if len(resposta) < 3:
        print("❌ Resposta muito curta.")
        return False
    dados_sem_crc = resposta[:-2]
    crc_recebido = resposta[-2:]
    crc_calculado = calcula_crc16(dados_sem_crc)
    crc_calc_bytes = struct.pack('>H', crc_calculado)
    if crc_recebido != crc_calc_bytes:
        print(f"❌ CRC inválido: recebido {crc_recebido.hex()}, esperado {crc_calc_bytes.hex()}")
        return False
    return True

# Função que converte Float24 (3 bytes) para Float32 (4 bytes) para facilitar a interpretação dos dados recebidos
def float24_to_float32(b1, b2, b3):
    raw = bytes([0x00, b1, b2, b3])
    return struct.unpack('<f', raw)[0]

# Função que aguarda o recebimento do byte ENQ do medidor, indicando que ele está pronto para receber comandos
def esperar_enq(sock, timeout=20):
    sock.settimeout(timeout)
    try:
        while True:
            byte = sock.recv(1)
            if not byte:
                return False
            if byte[0] == ENQ:
                return True
    except socket.timeout:
        return False

# Função que envia pacotes ALO para o medidor, iniciando a comunicação
def enviar_alo(sock):
    for _ in range(MAX_ALO):
        sock.sendall(bytes([ALO]))

# Função que envia pacotes UDP de ativação para o medidor, necessário para alguns modelos antes de iniciar a comunicação TCP
def enviar_pacote_udp_ativacao(ip_destino, num_tentativas=3, intervalo=1.0):
    print(f"\n📡 Enviando {num_tentativas} pacotes UDP de ativação para {ip_destino}:65535")
    mensagem = bytes.fromhex("020121c03803")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        for i in range(num_tentativas):
            try:
                udp_sock.sendto(mensagem, (ip_destino, 65535))
                print(f"\n🔸 Pacote UDP {i+1}/{num_tentativas} enviado.\n")
                time.sleep(intervalo)
            except Exception as e:
                print(f"\n⚠️ Erro ao enviar UDP: {e}\n")

# Função que gerencia o envio do comando, aguarda e interpreta a resposta do medidor, com tratamento de erros, timeouts e tentativas de reenvio conforme protocolo ABNT NBR 14522
def enviar_comando(sock, mensagem):
    nak_count = 0
    wait_count = 0
    retries = 0
    ip_destino = sock.getpeername()[0]

    while retries < MAX_RETRIES:
        print("\n🔌 Enviando ALO para iniciar conexão...\n")
        enviar_alo(sock)

        print("\nAguardando ENQ do medidor para enviar comando...\n")
        if not esperar_enq(sock, timeout=20):
            print("\nTimeout aguardando ENQ. Comando não enviado.\n")
            retries += 1
            continue

        print("\nENQ recebido, enviando comando.\n")
        sock.sendall(mensagem)

        try:
            resposta = sock.recv(512)
        except socket.timeout:
            print("\n ⏱️ Timeout ao receber resposta.\n")
            retries += 1
            continue

        if not resposta:
            print("\nNenhuma resposta recebida.\n")
            retries += 1
            continue

        resposta_complementada = resposta

        print(f"\nResposta recebida (hex): \n{resposta_complementada.hex().upper()}\n")
        primeiro_byte = resposta_complementada[0]

        if primeiro_byte == WAIT:
            wait_count += 1
            print(f"\nWAIT recebido ({wait_count}/{MAX_WAITS}), \naguardando ENQ para reenviar comando...\n")
            if wait_count > MAX_WAITS:
                print("\nNúmero máximo de WAITs atingido. Abortando.\n")
                break
            continue

        elif primeiro_byte == NAK:
            nak_count += 1
            print(f"\nNAK recebido ({nak_count}/{MAX_NAKS}), \nreenviando comando.\n")
            if nak_count > MAX_NAKS:
                print("\nNúmero máximo de NAKs atingido. Abortando.\n")
                break
            continue

        elif primeiro_byte == ENQ:
            print("\nENQ inesperado recebido, reenviando comando.\n")
            continue

        elif primeiro_byte == ACK:
            print("\nACK inesperado recebido, aguardando resposta.\n")
            continue

        else:
            if validar_crc_resposta(resposta_complementada):
                print("\nCRC válido na resposta, enviando ACK.\n")
                sock.sendall(bytes([ACK]))
                return resposta_complementada
            else:
                print("\nCRC inválido na resposta, enviando NAK.\n")
                sock.sendall(bytes([NAK]))
                nak_count += 1
                if nak_count > MAX_NAKS:
                    print("\nNúmero máximo de NAKs atingido. Abortando.\n")
                    break

                print("\n🔄 Reenviando pacotes de ativação UDP antes de nova tentativa.\n")
                enviar_pacote_udp_ativacao(ip_destino)
                continue

        retries += 1

    print("\nComunicação finalizada.\n")
    return None

def interpretar_float24_em_bloco(resposta: bytes):
    print("\n🧠 Interpretando possíveis Float24 na resposta:\n")
    for i in range(0, len(resposta) - 2, 3):
        bloco = resposta[i:i+3]
        if len(bloco) == 3:
            try:
                valor = float24_to_float32(bloco[0], bloco[1], bloco[2])
                print(f"\nOffset {i:03}: {valor:.6f}\n")
            except Exception:
                continue

def main():
    while True:
        print("\n=== Menu ===\n")
        ip = input("\nDigite o IP do medidor (ou 'sair' para terminar): \n").strip()
        if ip.lower() == 'sair':
            break

        porta_str = input("\nDigite a porta TCP do medidor: \n").strip()
        if not porta_str.isdigit():
            print("\nPorta inválida. Tente novamente.\n")
            continue
        porta = int(porta_str)

        cmd_str = input("\nDigite o número do comando (exemplo 14): \n").strip()
        if not cmd_str.isdigit():
            print("\nComando inválido. Tente novamente.\n")
            continue
        comando = int(cmd_str)

        numero_serie = 0x010203
        if comando == 14:
            numero_serie_str = input("\nDigite o número de série do leitor (exemplo 0x010203 ou decimal): \n").strip()
            if numero_serie_str.startswith("0x"):
                numero_serie = int(numero_serie_str, 16)
            elif numero_serie_str.isdigit():
                numero_serie = int(numero_serie_str)

        print(f"\nExecutando comando \n{comando} \npara medidor \n{ip}:{porta}\n")

        try:
            # Etapa de ativação inicial
            enviar_pacote_udp_ativacao(ip)

            with socket.create_connection((ip, porta), timeout=5) as sock:
                print("\nConectado ao medidor.\n")

                if comando == 14:
                    mensagem = montar_comando_14(numero_serie)
                else:
                    mensagem = montar_comando_generico(comando)

                resposta = enviar_comando(sock, mensagem)
                if resposta:
                    print("\n✅ Resposta válida recebida!\n")
                    interpretar_float24_em_bloco(resposta[1:-2])
                else:
                    print("\n❌ Falha na comunicação ou resposta inválida.\n")

        except Exception as e:
            print(f"\nErro na comunicação: {e}\n")

if __name__ == "__main__":
    main()
