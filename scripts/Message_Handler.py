#teste
import re
import tcp

_nick_dict = {}
_canal_dict = {}

def Message_Handler(conexao, dados):
    dados = dados.strip()
    if not dados:
        return sair(conexao)
    comandos = {
        b'PING': PING_handler,
        b'NICK': NICK_handler,
        b'JOIN': JOIN_handler,
        b'PRIVMSG': PRIVMSG_handler,
        b'PART': PART_handler,
    }
    comando = dados.split(b' ', 1)[0].upper()
    return comandos.get(comando, lambda c, d: (c, b''))(conexao, dados)

def PING_handler(conexao, dados):
    return conexao, b':server PONG server :' + dados.split(b' ', 1)[1] + b'\r\n'

def NICK_handler(conexao, dados):
    _, apelido = dados.split(b' ', 1)
    apelido_atual = _nick_dict.get(conexao, b'*')
    if not validar_nome(apelido):
        return conexao, b':server 432 ' + apelido_atual + b' ' + apelido + b' :Erroneous nickname\r\n'
    if apelido.lower() in _nick_dict.values():
        return conexao, b':server 433 ' + apelido_atual + b' ' + apelido + b' :Nickname is already in use\r\n'
    _nick_dict[conexao] = apelido.lower()
    if apelido_atual == b'*':
        return conexao, b':server 001 ' + apelido + b' :Welcome\r\n:server 422 ' + apelido + b' :MOTD File is missing\r\n'
    return conexao, b':' + apelido_atual + b' NICK ' + apelido + b'\r\n'

def PRIVMSG_handler(conexao, mensagem):
    sender = _nick_dict[conexao]
    _, receiver, conteudo = mensagem.split(maxsplit=2)
    if receiver.startswith(b'#'):
        return PRIVMSG_handler_canal(conexao, sender, receiver.lower(), conteudo.replace(b':', b''))
    if receiver.lower() not in _nick_dict.values():
        return conexao, b''
    target = list(_nick_dict.values()).index(receiver.lower())
    return list(_nick_dict.keys())[target], b':' + sender + b' PRIVMSG ' + receiver + b' ' + conteudo + b'\r\n'

def PRIVMSG_handler_canal(conexao, sender, canal, conteudo):
    canal = canal.lstrip(b'#')
    mensagem = b':' + sender + b' PRIVMSG #' + canal + b' :' + conteudo + b'\r\n'
    for conex in _canal_dict.get(canal, {}):
        if conex != conexao:
            conex.enviar(mensagem)
    return conexao, b''

def JOIN_handler(conexao, mensagem):
    canal = mensagem.split(b' ', 1)[1].lstrip(b'#').lower()
    if not validar_nome(canal):
        return conexao, b':server 403 ' + mensagem + b' :No such channel\r\n'
    if canal not in _canal_dict:
        _canal_dict[canal] = {}
    _canal_dict[canal][conexao] = _nick_dict[conexao]
    for conex in _canal_dict[canal]:
        if conex != conexao:
            conex.enviar(b':' + _nick_dict[conexao] + b' JOIN :#' + canal + b'\r\n')
    membros = b' '.join(sorted(_canal_dict[canal].values()))
    return conexao, (b':' + _nick_dict[conexao] + b' JOIN :#' + canal + b'\r\n' +
                     b':server 353 ' + _nick_dict[conexao] + b' = #' + canal + b' :' + membros + b'\r\n' +
                     b':server 366 ' + _nick_dict[conexao] + b' #' + canal + b' :End of /NAMES list.\r\n')

def PART_handler(conexao, dados):
    canal = dados.split(b' ', 2)[1].lstrip(b'#').lower()
    if canal in _canal_dict and conexao in _canal_dict[canal]:
        for conex in _canal_dict[canal]:
            conex.enviar(b':' + _nick_dict[conexao] + b' PART #' + canal + b'\r\n')
        _canal_dict[canal].pop(conexao, None)
    return conexao, b''

def validar_nome(nome):
    return re.match(br'^[a-zA-Z][a-zA-Z0-9_-]*$', nome) is not None

def sair(conexao):
    print(conexao, 'conexão fechada')
    conexao.fechar()
