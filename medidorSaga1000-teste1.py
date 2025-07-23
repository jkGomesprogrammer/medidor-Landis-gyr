import socket
from pyModbusTCP.utils import crc16
from pebble import concurrent, ProcessFuture
import struct

def is_data_hora_valida(bloco):
    if len(bloco) != 6:
        return False
    ano = 2000 + bloco[0]
    mes = bloco[1]
    dia = bloco[2]
    hora = bloco[3]
    minuto = bloco[4]
    segundo = bloco[5]
    if not (1 <= mes <= 12):
        return False
    if not (1 <= dia <= 31):
        return False
    if not (0 <= hora <= 23):
        return False
    if not (0 <= minuto <= 59):
        return False
    if not (0 <= segundo <= 59):
        return False
    return True

def interpretar_data_hora_t6(bloco):
    if not is_data_hora_valida(bloco):
        return "[data/hora inválida]"
    data = list(bloco)
    return f"{data[2]:02d}/{data[1]:02d}/{2000 + data[0]} {data[3]:02d}:{data[4]:02d}:{data[5]:02d}"


FORMATOS_COMANDO = {
    0x11: [("Resultado pedido início sessão", "A20")],  # texto livre / string
    0x12: [("Senha gerente", "A10")],                   # senha string (exemplo)
    0x13: [("Pedido string cálculo senha", "A20")],    # string para cálculo senha
    0x14: [                                           # Página fiscal (ABNT)
        ("Data/Hora", "T6"),
        ("Grandeza Instantânea 1", "F4"),
        ("Grandeza Instantânea 2", "F4"),
        ("Grandeza Instantânea 3", "F4"),
    ],
    0x20: [("Energia ativa", "F4"), ("Demanda", "F4"), ("Fator de potência", "F4")],
    0x21: [("Energia ativa atual", "F4"), ("Corrente média", "F4")],
    0x22: [("Energia ativa anterior", "F4"), ("Demanda anterior", "F4")],
    0x23: [("Registrador após última reposição", "F4")],
    0x24: [("Registrador última reposição demanda", "F4")],
    0x25: [("Período falta energia início", "T6"), ("Período falta energia fim", "T6")],
    0x26: [("Nº de série", "U4"), ("Data/Hora", "T6"), ("Valor 1", "F4"), ("Valor 2", "F4"), ("Valor 3", "F4")],
    0x27: [("Memória massa anterior", "A30")],  # exemplo genérico
    0x28: [("Registro alteração 1", "A10"), ("Registro alteração 2", "A10")],
    0x29: [("Nova data", "T6")],
    0x30: [("Nova hora", "T6")],
    0x31: [("Intervalo demanda", "U2")],
    0x32: [("Feriados nacionais", "A20")],
    0x33: [("Constantes multiplicação", "F4")],
    0x35: [("Segmentos horários", "A10")],
    0x36: [("Horário reservado", "A10")],
    0x37: [("Condição ocorrência registrador digital", "B1")],
    0x38: [("Inicialização registrador digital", "A10")],
    0x39: [("Resposta comando não implementado", "A20")],
    0x40: [("Ocorrência registrador digital", "A20")],
    0x41: [("Registros anteriores canal 1", "F4")],
    0x42: [("Registros anteriores canal 2", "F4")],
    0x43: [("Registros anteriores canal 3", "F4")],
    0x44: [("Registros atuais canal 1", "F4")],
    0x45: [("Registros atuais canal 2", "F4")],
    0x46: [("Registros atuais canal 3", "F4")],
    0x47: [("Forma cálculo demanda máxima", "A10")],
    0x51: [("Parâmetros sem reposição com memória de massa", "A30")],
    0x52: [("Memória massa completa", "A50")],
    0x53: [("Inicialização carga programa", "A10")],
    0x54: [("Transferência programa", "A10")],
    0x55: [("Finalização carga programa", "A10")],
    0x63: [("Data/hora execução reposição automática", "T6")],
    0x64: [("Alteração horário de verão", "A10")],
    0x65: [("Alteração conjunto 2 segmentos horários", "A10")],
    0x66: [("Alteração grandezas canais", "A20")],
    0x67: [("Alteração tarifa reativos", "A20")],
    0x73: [("Alteração intervalo memória massa", "U2")],
    0x77: [("Segmentos sábados/domingos/feriados", "A10")],
    0x78: [("Alteração tipo tarifa", "A10")],
    0x79: [("Condição visualização códigos mostrador", "A10")],
    0x80: [("Fator PT", "F4"), ("Fator TC", "F4"), ("Constante Energia", "F4"), ("Identificação", "A14")],
    0x81: [("Alteração serial consumidor estendida", "A20")],
    0x87: [("Alteração/Leitura código instalação", "A20")],
    0x90: [("Alteração modo apresentação grandezas", "A10")],
    0x95: [("Alteração constantes TP, TC e Ke", "F4"), ("Usuário", "A10")],
    0x98: [
        ("Comando estendido", "A10"),
        ("Subcomando", "U1"),
        # exemplo para subcomandos:
        # cmd 98[12] - Cadastro senha usuário
        # cmd 98[30] - Micro ajuste relógio
        # cmd 98[32] - Feriados estendido
    ],
    # para os subcomandos de 0x98 você pode ter outro dict para diferenciar
}

def interpretar_bloco_bytes(bloco: bytes, tipo: str):
    try:
        if tipo.startswith("F"):  # Float 4 bytes
            if len(bloco) != 4:
                return f"[erro: tamanho incorreto para float: {len(bloco)} bytes]"
            val_le = struct.unpack("<f", bloco)[0]
            return round(val_le, 4)

        elif tipo.startswith("U"):  # Unsigned int
            return int.from_bytes(bloco, byteorder='big', signed=False)

        elif tipo.startswith("I"):  # Signed int
            return int.from_bytes(bloco, byteorder='big', signed=True)

        elif tipo.startswith("A"):  # ASCII
            return bloco.decode('ascii', errors='ignore').rstrip('\x00 ').strip()

        elif tipo.startswith("B"):  # Bits
            bin_str = bin(int.from_bytes(bloco, byteorder='big'))[2:].zfill(len(bloco)*8)
            return f"0b{bin_str}"

        elif tipo.startswith("T"):  # Data/hora T6
            if not is_data_hora_valida(bloco):
                return "[data/hora inválida]"
            data = list(bloco)
            return f"{data[2]:02d}/{data[1]:02d}/{2000 + data[0]} {data[3]:02d}:{data[4]:02d}:{data[5]:02d}"

        else:
            return bloco.hex()
    except Exception as e:
        return f"[erro: {e}]"
# Função para filtrar bytes de controle (comuns na resposta Saga 1000)
def filtrar_bytes_resposta(resposta: bytes) -> bytes:
    bytes_controle = {0xFF, 0xFB, 0xFD}
    return bytes(b for b in resposta if b not in bytes_controle)

def interpretar_resposta_bytes(resposta: bytes):
    # 1. Filtrar bytes de controle
    resposta_limpa = filtrar_bytes_resposta(resposta)

    # 2. Procurar início da mensagem padrão 0x01 0x99
    inicio = resposta_limpa.find(b'\x01\x99')
    if inicio == -1:
        print("❌ Início da resposta (01 99) não encontrado.")
        return

    resposta_msg = resposta_limpa[inicio:]
    if len(resposta_msg) < 4:
        print("❌ Resposta muito curta após início.")
        return

    comando = resposta_msg[2]
    print(f"\n🔍 Comando identificado: {comando} (0x{comando:02X})")

    estrutura = FORMATOS_COMANDO.get(comando)
    if not estrutura:
        print("⚠️ Comando não mapeado. Dados brutos:")
        print(resposta_msg.hex())
        return

    print(f"📘 Estrutura definida para o comando 0x{comando:02X}:")
    pos = 4  # Após 01 99, comando e byte extra
    for nome, tipo in estrutura:
        n_bytes = int(tipo[1:])
        bloco = resposta_msg[pos:pos + n_bytes]
        if len(bloco) < n_bytes:
            print(f"[{pos:03d}] {nome:<25} ({tipo}): [dados insuficientes]")
            break
        valor = interpretar_bloco_bytes(bloco, tipo)
        print(f"[{pos:03d}] {nome:<25} ({tipo}): {valor}")
        pos += n_bytes

    print("\n✅ Fim da interpretação.\n")

def inspecionar_offsets_bytes(resposta: bytes, comando=0x80):
    inicio = resposta.find(b'\x01\x99')
    if inicio == -1:
        print("❌ Início de resposta (01 99) não encontrado.")
        return

    resposta = resposta[inicio:]
    estrutura = FORMATOS_COMANDO.get(comando)
    if not estrutura:
        print(f"⚠️ Comando 0x{comando:02X} não mapeado.")
        return

    print(f"🔎 Inspeção automática para comando 0x{comando:02X} testando offsets...\n")

    max_offset = 30
    for pos_test in range(max_offset):
        pos = pos_test
        print(f"--- Offset inicial = {pos_test} ---")
        try:
            for nome, tipo in estrutura:
                n_bytes = int(tipo[1:])
                bloco = resposta[pos:pos + n_bytes]
                valor = interpretar_bloco_bytes(bloco, tipo)
                print(f"[{pos:03d}] {nome:<25} ({tipo}): {valor}")
                pos += n_bytes
        except Exception as e:
            print(f"Erro no offset {pos_test}: {e}")
        print()


class ComunicacaoNBR:
    def __init__(self, ip: str, port: int) -> None:
        self.__IP = ip
        self.__PORT = port

    def __conexao_socket(self) -> socket.socket:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.__IP, self.__PORT))
            return sock
        except Exception as e:
            raise ConnectionError(f'Erro de conexão: {e}')

    def __montar_hex_comando(self, comando: int, leitora: int, parametro='00') -> bytes:
        msg = bytearray()
        msg.extend(b'\x01\x99')  # cabeçalho fixo
        msg.append(comando)
        msg.append(leitora)
        msg.append(int(parametro, 16))
        while len(msg) < 66:
            msg.append(0)
        crc_val = crc16(msg)
        crc_bytes = crc_val.to_bytes(2, byteorder='little')  # CRC little endian
        msg.extend(crc_bytes)
        return bytes(msg)

    @concurrent.process(timeout=20)
    def __envio_comando(self, comando_bytes: bytes) -> ProcessFuture:
        try:
            conexao = self.__conexao_socket()
            conexao.sendall(comando_bytes)
            resposta = conexao.recv(260)
            while len(resposta) < 66:
                resposta += conexao.recv(260)
            conexao.close()
            return resposta
        except Exception as e:
            raise ConnectionError(f'Erro ao enviar comando: {e}')

    def enviar_comando(self, comando: int, leitora: int, parametro: str = '00') -> bytes:
        try:
            comando_bytes = self.__montar_hex_comando(comando, leitora, parametro)
            futuro = self.__envio_comando(comando_bytes)
            return futuro.result()
        except TimeoutError:
            raise TimeoutError("⏰ Tempo limite excedido para resposta.")
        except Exception as e:
            raise RuntimeError(f'Erro ao enviar comando: {e}')


def main():
    com = ComunicacaoNBR('172.16.0.42', 5001)
    try:
        resposta = com.enviar_comando(0x51, 0x00, '00')
        print("\nResposta bruta (bytes):", resposta)
        interpretar_resposta_bytes(resposta)
        inspecionar_offsets_bytes(resposta, comando=0x51)
    except Exception as erro:
        print(f"Erro: {erro}")


if __name__ == "__main__":
    main()
