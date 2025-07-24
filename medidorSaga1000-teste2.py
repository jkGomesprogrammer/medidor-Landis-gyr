import struct
import socket
import time

ENQ = 0x05
ACK = 0x06
NAK = 0x15
WAIT = 0x10
ALO = 0xFF

MAX_NAKS = 7
MAX_WAITS = 12
MAX_RETRIES = 7
MAX_ALO = 5

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

def complementar_bytes(data: bytes) -> bytes:
    return bytes((~b) & 0xFF for b in data)

def montar_comando_generico(codigo: int, argumento: int = 0x00):
    comando = 0x63
    dados_sem_crc = bytes([codigo, comando, argumento])
    crc = calcula_crc16(dados_sem_crc)
    crc_bytes = struct.pack('>H', crc)
    dados_completos = dados_sem_crc + crc_bytes
    dados_complementados = complementar_bytes(dados_completos)
    mensagem = bytes([ENQ]) + dados_complementados
    return mensagem

def montar_comando_14(numero_serie: int):
    dados = bytes([0x14]) + numero_serie.to_bytes(3, 'big') + bytes(60)
    crc = calcula_crc16(dados)
    crc_bytes = struct.pack('>H', crc)
    dados_completos = dados + crc_bytes
    dados_complementados = complementar_bytes(dados_completos)
    return dados_complementados

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

def float24_to_float32(b1, b2, b3):
    raw = bytes([0x00, b1, b2, b3])
    return struct.unpack('<f', raw)[0]

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

def enviar_alo(sock):
    for _ in range(MAX_ALO):
        sock.sendall(bytes([ALO]))

def enviar_pacote_udp_ativacao(ip_destino, num_tentativas=3, intervalo=1.0):
    print(f"\n📡 Enviando {num_tentativas} pacotes UDP de ativação para {ip_destino}:65535")
    mensagem = bytes.fromhex("020121c03803")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
        for i in range(num_tentativas):
            try:
                udp_sock.sendto(mensagem, (ip_destino, 65535))
                print(f"🔸 Pacote UDP {i+1}/{num_tentativas} enviado.")
                time.sleep(intervalo)
            except Exception as e:
                print(f"⚠️ Erro ao enviar UDP: {e}")

def enviar_comando(sock, mensagem):
    nak_count = 0
    wait_count = 0
    retries = 0
    ip_destino = sock.getpeername()[0]

    while retries < MAX_RETRIES:
        print("Enviando ALO para iniciar conexão...")
        enviar_alo(sock)

        print("Aguardando ENQ do medidor para enviar comando...")
        if not esperar_enq(sock, timeout=20):
            print("Timeout aguardando ENQ. Comando não enviado.")
            retries += 1
            continue

        print("ENQ recebido, enviando comando.")
        sock.sendall(mensagem)

        try:
            resposta = sock.recv(512)
        except socket.timeout:
            print("⏱️ Timeout ao receber resposta.")
            retries += 1
            continue

        if not resposta:
            print("Nenhuma resposta recebida.")
            retries += 1
            continue

        # ⚠️ REMOVIDO complemento extra
        resposta_complementada = resposta

        print(f"Resposta recebida (hex): {resposta_complementada.hex().upper()}")
        primeiro_byte = resposta_complementada[0]

        if primeiro_byte == WAIT:
            wait_count += 1
            print(f"WAIT recebido ({wait_count}/{MAX_WAITS}), aguardando ENQ para reenviar comando...")
            if wait_count > MAX_WAITS:
                print("Número máximo de WAITs atingido. Abortando.")
                break
            continue

        elif primeiro_byte == NAK:
            nak_count += 1
            print(f"NAK recebido ({nak_count}/{MAX_NAKS}), reenviando comando.")
            if nak_count > MAX_NAKS:
                print("Número máximo de NAKs atingido. Abortando.")
                break
            continue

        elif primeiro_byte == ENQ:
            print("ENQ inesperado recebido, reenviando comando.")
            continue

        elif primeiro_byte == ACK:
            print("ACK inesperado recebido, aguardando resposta.")
            continue

        else:
            if validar_crc_resposta(resposta_complementada):
                print("CRC válido na resposta, enviando ACK.")
                sock.sendall(bytes([ACK]))
                return resposta_complementada
            else:
                print("CRC inválido na resposta, enviando NAK.")
                sock.sendall(bytes([NAK]))
                nak_count += 1
                if nak_count > MAX_NAKS:
                    print("Número máximo de NAKs atingido. Abortando.")
                    break

                # ⚠️ NOVO: reenviar pacotes UDP após erro
                print("🔄 Reenviando pacotes de ativação UDP antes de nova tentativa.")
                enviar_pacote_udp_ativacao(ip_destino)
                continue

        retries += 1

    print("Comunicação finalizada.")
    return None

def interpretar_float24_em_bloco(resposta: bytes):
    print("\n🧠 Interpretando possíveis Float24 na resposta:")
    for i in range(0, len(resposta) - 2, 3):
        bloco = resposta[i:i+3]
        if len(bloco) == 3:
            try:
                valor = float24_to_float32(bloco[0], bloco[1], bloco[2])
                print(f"Offset {i:03}: {valor:.6f}")
            except Exception:
                continue

def main():
    while True:
        print("\n=== Menu ===")
        ip = input("Digite o IP do medidor (ou 'sair' para terminar): ").strip()
        if ip.lower() == 'sair':
            break

        porta_str = input("Digite a porta TCP do medidor: ").strip()
        if not porta_str.isdigit():
            print("Porta inválida. Tente novamente.")
            continue
        porta = int(porta_str)

        cmd_str = input("Digite o número do comando (exemplo 14): ").strip()
        if not cmd_str.isdigit():
            print("Comando inválido. Tente novamente.")
            continue
        comando = int(cmd_str)

        numero_serie = 0x010203
        if comando == 14:
            numero_serie_str = input("Digite o número de série do leitor (exemplo 0x010203 ou decimal): ").strip()
            if numero_serie_str.startswith("0x"):
                numero_serie = int(numero_serie_str, 16)
            elif numero_serie_str.isdigit():
                numero_serie = int(numero_serie_str)

        print(f"\nExecutando comando {comando} para medidor {ip}:{porta}")

        try:
            # Etapa de ativação inicial
            enviar_pacote_udp_ativacao(ip)

            with socket.create_connection((ip, porta), timeout=5) as sock:
                print("Conectado ao medidor.")

                if comando == 14:
                    mensagem = montar_comando_14(numero_serie)
                else:
                    mensagem = montar_comando_generico(comando)

                resposta = enviar_comando(sock, mensagem)
                if resposta:
                    print("✅ Resposta válida recebida!")
                    interpretar_float24_em_bloco(resposta[1:-2])
                else:
                    print("❌ Falha na comunicação ou resposta inválida.")

        except Exception as e:
            print(f"Erro na comunicação: {e}")

if __name__ == "__main__":
    main()
