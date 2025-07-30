import os
import socket
from dotenv import load_dotenv

load_dotenv() 

gateway_ip = os.getenv('GATEWAY_IP')
gateway_port = int(os.getenv('GATEWAY_PORT', '1001')) 
endereco_logico = int(os.getenv('ENDERECO_LOGICO', '1'))
codigo_funcao = int(os.getenv('CODIGO_FUNCAO', '1'))
enviar_enq = os.getenv('ENVIAR_ENQ', 'False').lower() == 'true'


# ========= FUNÇÕES =========

def calcular_crc_abnt(dados):
    """
    Calcula o CRC-16 padrão ABNT (CRC-16/ANSI) com polinômio 0x8005, MSB-first.
    """
    crc = 0x0000
    for byte in dados:
        crc ^= (byte << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ 0x8005
            else:
                crc <<= 1
            crc &= 0xFFFF  
    return crc

def montar_comando_abnt(endereco, codigo, dados=b''):
    corpo = bytearray()
    corpo.append(endereco)
    corpo.append(codigo)
    corpo.extend(dados)

    crc = calcular_crc_abnt(corpo)
    crc_bytes = crc.to_bytes(2, byteorder='big')  

    frame = bytearray()
    frame.append(0x02)         
    frame.extend(corpo)        
    frame.extend(crc_bytes)    
    frame.append(0x03)         
    return bytes(frame)

def receber_resposta(sock, timeout=5):
    sock.settimeout(timeout)
    dados = bytearray()
    try:
        while True:
            parte = sock.recv(64)
            if not parte:
                break
            dados.extend(parte)
            if 0x03 in parte:  
                break
    except socket.timeout:
        pass
    return bytes(dados)

def imprimir_resposta_hexa(resposta_bytes):
    print("Resposta recebida (hex):")
    print(resposta_bytes.hex(' '))
    print(f"Tamanho da resposta: {len(resposta_bytes)} bytes")

# ========= EXECUÇÃO =========

try:
    print(f"[1] Conectando ao gateway {gateway_ip}:{gateway_port}...")
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.settimeout(20)
    tcp_socket.connect((gateway_ip, gateway_port))
    print("[2] Conexão TCP estabelecida com sucesso.")

    if enviar_enq:
        enq = bytes([0x05])
        print(f"[3] Enviando ENQ: {enq.hex()}")
        tcp_socket.send(enq)
        resposta_enq = receber_resposta(tcp_socket, timeout=3)
        if resposta_enq:
            print(f"[4] Resposta ao ENQ: {resposta_enq.hex()}")
        else:
            print("[4] Nenhuma resposta ao ENQ.")

    comando = montar_comando_abnt(endereco_logico, codigo_funcao)
    print(f"[5] Enviando comando ABNT: {comando.hex()}")
    tcp_socket.send(comando)

    resposta = receber_resposta(tcp_socket, timeout=5)
    if resposta:
        print(f"[6] Resposta do medidor ({len(resposta)} bytes):")
        imprimir_resposta_hexa(resposta)
    else:
        print("[6] Nenhuma resposta do medidor.")

except socket.timeout:
    print("[!] Timeout: O medidor não respondeu.")
except ConnectionRefusedError:
    print("[!] Conexão recusada: Verifique IP e porta.")
except Exception as e:
    print(f"[!] Erro: {e}")
finally:
    tcp_socket.close()
    print("[7] Conexão encerrada.")

