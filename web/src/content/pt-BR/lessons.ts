// Course content in pt-BR. General, verifiable guidance: no made-up statistics or cases.
// Every scam lesson is written in our own words from the FEBRABAN anti-fraud pages it cites.
// Quiz messages quote real scam wording, so they may speak in the first person.
import type { Lesson, LessonSource } from '../lessons'

export const SOURCES_ACCESSED_ON = '18/11/2026'

// One page per scam under portal.febraban.org.br/AntiFraude ("Golpes mais comuns").
const febraban = (id: number, title: string): LessonSource => ({
  title: `FEBRABAN, ${title}`,
  url: `https://portal.febraban.org.br/DetalheAntifraude/${id}/pt-br/`,
})

export const GOLDEN_RULES: string[] = [
  'Pressa é sinal de golpe. Quem é de verdade espera você confirmar.',
  'Ninguém de confiança pede senha, código ou token por mensagem ou ligação.',
  'Confirme por outro caminho: ligue você mesmo para o número que já conhece.',
  'Não clique em links de mensagens que você não esperava.',
  'Na dúvida, confira no Verifica AI ou pergunte a alguém de confiança.',
]

export const LESSONS: Lesson[] = [
  {
    id: 'falso-parente',
    title: 'Golpe do falso parente',
    summary: 'Alguém finge ser da família, com número novo, e pede dinheiro.',
    howItWorks:
      'O golpista manda mensagem dizendo que é seu filho, neto ou outro parente e que trocou de número. Às vezes ele usa a conta de WhatsApp roubada de alguém que você conhece. Pouco depois, pede um Pix ou o pagamento de uma conta com urgência.',
    signs: [
      'A mensagem vem de um número que você não conhece.',
      'Pede dinheiro logo nas primeiras mensagens.',
      'Dá desculpas para não atender ligação ("estou sem sinal", "não posso falar agora").',
    ],
    doThis: [
      'Ligue para o número antigo da pessoa, o que você já tem salvo.',
      'Faça uma pergunta que só a pessoa de verdade saberia responder.',
      'Não mande dinheiro antes de falar com ela por voz.',
    ],
    quiz: {
      message: 'Pai, perdi meu celular e esse é meu número novo. Consegue pagar um boleto pra mim hoje? Depois te devolvo.',
      isScam: true,
      explanation: 'Número novo, pedido de dinheiro e pressa: são os três sinais do falso parente. Ligue para o número antigo antes de qualquer coisa.',
    },
    sources: [febraban(7, 'Golpe do Whatsapp')],
  },
  {
    id: 'central-banco',
    title: 'Falsa central do banco',
    summary: 'Ligação ou SMS fingindo ser do banco para pegar senha ou dinheiro.',
    howItWorks:
      'Alguém liga ou manda SMS avisando de uma compra suspeita ou de uma conta invadida. Para "proteger" a conta, pede sua senha, um código, que você instale um aplicativo ou transfira o dinheiro para uma "conta segura". O aplicativo, se instalado, deixa o golpista mexer no seu celular.',
    signs: [
      'Pede senha, código que chegou por SMS ou número do token.',
      'Pede para instalar um aplicativo ou transferir dinheiro para "proteger" a conta.',
      'O SMS manda você ligar para um número que está na própria mensagem.',
    ],
    doThis: [
      'Desligue. Não continue a conversa.',
      'Ligue você mesmo para o número que está no verso do seu cartão, de preferência de outro telefone.',
      'Lembre: o banco não pede senha, não pede para instalar aplicativo e não pede para você transferir dinheiro para proteger a conta.',
    ],
    quiz: {
      message: 'BANCO: Compra de R$ 2.890,00 aprovada no seu cartão. Não reconhece? Ligue agora para 0800 000 0000.',
      isScam: true,
      explanation: 'O número para ligar está na própria mensagem, que é como o golpe começa. Confira a compra no aplicativo do banco ou ligue para o número do verso do cartão.',
    },
    sources: [febraban(2, 'Golpe da falsa central de atendimento'), febraban(9, 'Golpe acesso remoto ou mão fantasma')],
  },
  {
    id: 'falso-motoboy',
    title: 'Falso motoboy',
    summary: 'Pedem para você cortar o cartão e entregar a um "funcionário do banco".',
    howItWorks:
      'Alguém liga dizendo ser do banco e avisa que o seu cartão foi usado por golpistas. Pede a senha e manda cortar o cartão, mas sem estragar o chip. Depois diz que um motoboy vai buscar o cartão na sua casa. Quem vem buscar é cúmplice, e o chip inteiro é usado para fazer compras.',
    signs: [
      'Pedem para você cortar o cartão e guardar o chip.',
      'Dizem que alguém vai buscar o cartão na sua casa.',
      'Pedem a senha do cartão pelo telefone.',
    ],
    doThis: [
      'Desligue na hora.',
      'Nunca entregue seu cartão a ninguém: o banco não recolhe cartões nem manda buscar em casa.',
      'Ligue você mesmo para o número do verso do cartão para conferir.',
    ],
    quiz: {
      message: 'Aqui é do setor de segurança do seu banco. Seu cartão foi clonado. Corte ele ao meio sem danificar o chip, que um portador vai buscar ainda hoje.',
      isScam: true,
      explanation: 'O banco nunca pede para cortar o cartão nem manda buscar em casa. Quem pede isso é golpista.',
    },
    sources: [febraban(3, 'Golpe do falso motoboy')],
  },
  {
    id: 'codigo-whatsapp',
    title: 'Código do WhatsApp',
    summary: 'Pedem o código que chegou por SMS para roubar sua conta.',
    howItWorks:
      'O golpista tenta entrar no WhatsApp com o seu número. O aplicativo manda um código para o seu celular, e ele pede esse código fingindo ter mandado por engano ou ser de uma empresa, para uma "atualização" ou "confirmação de cadastro".',
    signs: [
      'Alguém pede um código de 6 números que chegou para você.',
      'Diz que mandou o código "por engano".',
      'Fala em nome de uma loja, pesquisa ou sorteio.',
    ],
    doThis: [
      'Nunca passe códigos que chegarem por SMS, para ninguém.',
      'Ative a confirmação em duas etapas no WhatsApp: Configurações, depois Conta, depois Confirmação em duas etapas.',
      'Deixe sua foto de perfil visível só para seus contatos.',
      'Se perder o acesso, avise seus contatos por outro meio para não caírem no golpe.',
    ],
    quiz: {
      message: 'Oi! Te mandei um código de 6 números por engano. Pode me passar, por favor?',
      isScam: true,
      explanation: 'Esse código dá acesso à sua conta. Quem tiver ele pode falar com seus contatos fingindo ser você.',
    },
    sources: [febraban(7, 'Golpe do Whatsapp')],
  },
  {
    id: 'links-falsos',
    title: 'Links e sites falsos',
    summary: 'Páginas que imitam banco, governo ou loja para roubar seus dados.',
    howItWorks:
      'A mensagem traz um link para um site muito parecido com o verdadeiro. Lá, pede senha, dados do cartão ou CPF. Às vezes ameaça bloquear algo se você não "regularizar" logo, ou promete dinheiro, como uma falsa restituição do Imposto de Renda.',
    signs: [
      'O endereço tem letras trocadas ou palavras a mais, como "atualiza", "regulariza" ou "seguro".',
      'Promoção boa demais, dinheiro para receber ou ameaça de bloqueio com prazo curto.',
      'O site pede senha ou dados do cartão logo de cara.',
    ],
    doThis: [
      'Não clique no link da mensagem.',
      'Abra o aplicativo oficial ou digite você mesmo o endereço que já conhece.',
      'Antes de abrir, cole o link no Verifica AI para conferir.',
    ],
    quiz: {
      message: 'Seu CPF será bloqueado hoje. Regularize em gov-br-regulariza.com para evitar multa.',
      isScam: true,
      explanation: 'Ameaça com prazo curto e um endereço que imita o do governo. Sites oficiais do governo terminam em .gov.br, sem palavras a mais no meio.',
    },
    sources: [
      febraban(8, 'Golpe do link falso (Phishing - Pescaria Digital)'),
      febraban(12, 'Golpe da restituição do imposto de renda'),
    ],
  },
  {
    id: 'pix-boleto',
    title: 'Pix, boletos e QR Code',
    summary: 'Cobranças falsas que mandam o dinheiro para a pessoa errada.',
    howItWorks:
      'Chega um boleto ou um QR Code com desconto ou cobrança urgente. O golpista troca os dados de quem recebe, e na hora de pagar o dinheiro vai para a conta dele, e não para a empresa.',
    signs: [
      'Boleto ou cobrança que chegou por mensagem, sem você esperar.',
      'O nome de quem vai receber, na tela do banco, não é o da empresa.',
      'Desconto grande para pagar "só hoje".',
    ],
    doThis: [
      'Antes de confirmar, leia o nome de quem vai receber na tela do banco e compare com o boleto.',
      'Se o nome não for o da empresa, não pague. Na dúvida, ligue para o atendimento da empresa.',
      'Pegue boletos no site ou aplicativo oficial da empresa.',
    ],
    quiz: {
      message: 'Conta de luz com 50% de desconto para pagamento hoje! Pague pelo boleto em anexo.',
      isScam: true,
      explanation: 'Desconto grande e prazo curto, num boleto que chegou por mensagem. Pegue a conta no site ou aplicativo da companhia de luz.',
    },
    sources: [febraban(14, 'Golpe Falso Boleto')],
  },
  {
    id: 'pix-errado',
    title: 'Pix por engano',
    summary: 'Mandam um Pix "por engano" e pedem a devolução para outra conta.',
    howItWorks:
      'Você recebe um Pix de alguém que não conhece. Logo depois, a pessoa diz que errou e pede a devolução, mas para outra chave Pix. Depois que você devolve, o golpista pede ao banco o estorno do Pix original. Assim, você perde o dinheiro duas vezes.',
    signs: [
      'Chega um Pix que você não esperava, seguido de um pedido para devolver.',
      'A pessoa pede a devolução para uma chave diferente da que mandou o dinheiro.',
      'Insiste e tem pressa.',
    ],
    doThis: [
      'Não faça um Pix novo para outra chave.',
      'Se for devolver, use a opção "devolver" do próprio Pix recebido, no aplicativo do banco. Ela manda o dinheiro de volta para a conta de origem.',
      'Na dúvida, fale com o seu banco pelo aplicativo ou pelo número do verso do cartão.',
    ],
    quiz: {
      message: 'Moço, te mandei um Pix de R$ 500 sem querer! Pode devolver nessa chave aqui? É do meu marido.',
      isScam: true,
      explanation: 'Pedir a devolução para outra chave é o sinal do golpe. Devolva só pela opção "devolver" do Pix recebido, que volta para a conta certa.',
    },
    sources: [febraban(1, 'Golpe do Pix errado')],
  },
  {
    id: 'maquininha',
    title: 'Maquininha e troca de cartão',
    summary: 'Na hora de pagar, cobram a mais ou trocam o seu cartão.',
    howItWorks:
      'Numa entrega ou numa loja, a maquininha está com o visor quebrado ou virada para você não ver o valor, e a cobrança sai bem maior. Outra versão: pedem uma "taxa de entrega" para um pedido que já foi pago no aplicativo. Há também quem olhe você digitar a senha e devolva outro cartão no lugar do seu.',
    signs: [
      'A tela da maquininha está quebrada ou escondida.',
      'Pedem para pagar de novo algo que você já pagou.',
      'Alguém se oferece para "ajudar" no caixa eletrônico ou pega o seu cartão da sua mão.',
    ],
    doThis: [
      'Não pague em maquininha com o visor quebrado.',
      'Confira o valor na tela antes de digitar a senha.',
      'Coloque você mesmo o cartão na máquina e confira se o cartão devolvido é o seu.',
    ],
    quiz: {
      message: 'O entregador diz: "O visor da máquina quebrou, mas pode passar o cartão e digitar a senha, que está certo o valor".',
      isScam: true,
      explanation: 'Sem ver o valor na tela, você não sabe quanto está pagando. Não pague em maquininha com visor quebrado.',
    },
    sources: [febraban(5, 'Golpe da maquininha quebrada'), febraban(4, 'Golpe da troca de cartão')],
  },
  {
    id: 'falso-emprestimo',
    title: 'Falso empréstimo',
    summary: 'Oferecem crédito fácil, mas cobram uma taxa antes de liberar.',
    howItWorks:
      'Uma suposta financeira oferece empréstimo com taxa muito boa, por anúncio, mensagem ou ligação. Depois do cadastro, manda um "contrato" e diz que, para liberar o dinheiro, você precisa pagar uma taxa ou imposto antes. O empréstimo nunca chega.',
    signs: [
      'Pedem pagamento antecipado para liberar o empréstimo.',
      'A taxa oferecida é boa demais.',
      'Ligam ou mandam mensagem oferecendo crédito sem você ter pedido.',
    ],
    doThis: [
      'Lembre: nenhum empréstimo de verdade exige pagamento antes de liberar o dinheiro.',
      'Se pedirem transferência para "confirmar", desligue.',
      'Procure crédito só no aplicativo ou na agência do seu banco.',
    ],
    quiz: {
      message: 'Seu empréstimo de R$ 15.000 foi aprovado! Para liberar hoje, pague a taxa de cadastro de R$ 390 via Pix.',
      isScam: true,
      explanation: 'Taxa antes de liberar o dinheiro é sempre golpe. Empréstimo de verdade desconta os custos das parcelas, não cobra antes.',
    },
    sources: [febraban(10, 'Golpe do falso empréstimo')],
  },
  {
    id: 'falso-investimento',
    title: 'Falso investimento',
    summary: 'Prometem lucro alto e rápido para ficar com o seu dinheiro.',
    howItWorks:
      'Oferecem um investimento que rende muito e muito rápido. No começo, até pagam um pouco, para ganhar confiança. Quando você coloca mais dinheiro, eles somem.',
    signs: [
      'Promessa de ganhar muito em pouco tempo.',
      'Os primeiros lucros chegam rápido, para você investir mais.',
      'Pressa para entrar "antes que acabe a oportunidade".',
    ],
    doThis: [
      'Desconfie: não existe dinheiro fácil.',
      'Não faça transferências para investimentos que prometem lucro alto e rápido.',
      'Antes de investir, converse com o seu banco ou com alguém de confiança.',
    ],
    quiz: {
      message: 'Invista R$ 200 hoje e receba R$ 2.000 em 7 dias! Vagas limitadas, só até meia-noite.',
      isScam: true,
      explanation: 'Lucro alto, rápido e com pressa para entrar: é a cara do falso investimento. Ninguém multiplica dinheiro assim.',
    },
    sources: [febraban(11, 'Golpe do falso investimento')],
  },
  {
    id: 'compras-falsas',
    title: 'Lojas e leilões falsos',
    summary: 'Sites e perfis com preço baixo demais que nunca entregam.',
    howItWorks:
      'Golpistas criam lojas, perfis em redes sociais e sites de leilão falsos, com produtos muito abaixo do preço normal. Pedem Pix ou depósito para "garantir" a compra, com pressa para você não perder o desconto. O produto nunca chega, e às vezes ainda roubam seus dados.',
    signs: [
      'Preço muito abaixo do normal.',
      'Loja ou perfil criado há pouco tempo, ou com poucas formas de pagamento.',
      'Pedem Pix ou depósito na conta de uma pessoa, e não de uma empresa.',
    ],
    doThis: [
      'Prefira lojas que você já conhece.',
      'Pesquise a empresa em sites de reclamação e confira o CNPJ.',
      'Não pague para a conta de uma pessoa física.',
    ],
    quiz: {
      message: 'LEILÃO: carro 2022 por R$ 9.900! Faça o Pix de reserva agora, as vagas acabam hoje.',
      isScam: true,
      explanation: 'Preço muito abaixo do normal, Pix para "reservar" e pressa: são sinais de leilão falso.',
    },
    sources: [febraban(13, 'Golpe Falsa Venda'), febraban(6, 'Golpe do falso leilão')],
  },
  {
    id: 'falso-advogado',
    title: 'Falso advogado',
    summary: 'Usam o nome de um advogado para cobrar e "liberar" um dinheiro de processo.',
    howItWorks:
      'O golpista usa o nome, a foto e dados reais de um advogado ou escritório. Manda mensagem dizendo que você ganhou um processo ou tem dinheiro para receber, mas que precisa pagar antes custas, honorários ou impostos, quase sempre por Pix. Pode mandar documentos falsos e links.',
    signs: [
      'Número desconhecido dizendo ser o seu advogado.',
      'Pede pagamento para liberar indenização ou dinheiro de processo.',
      'Pressa para pagar e pedido de dados pessoais por mensagem.',
    ],
    doThis: [
      'Nunca pague para liberar dinheiro de processo.',
      'Confirme com o seu advogado pelo telefone ou contato que você já usava.',
      'Se pagou ou passou dados, guarde as mensagens, avise o banco e registre um boletim de ocorrência.',
    ],
    quiz: {
      message: 'Dr. Paulo aqui, do escritório. Seu processo foi ganho! Para liberar os R$ 18 mil, pague as custas de R$ 750 por Pix hoje.',
      isScam: true,
      explanation: 'Número novo, dinheiro para receber e cobrança antes: ligue para o seu advogado no número de sempre antes de qualquer coisa.',
    },
    sources: [febraban(19, 'Golpe do falso advogado')],
  },
  {
    id: 'mensagens-normais',
    title: 'Nem tudo é golpe',
    summary: 'Como reconhecer uma mensagem que provavelmente é verdadeira.',
    howItWorks:
      'Muitas mensagens são legítimas: lembrete de consulta, aviso de entrega de uma compra que você fez. O segredo é olhar o que ela pede de você.',
    signs: [
      'Não pede dinheiro, senha nem código.',
      'Não tem pressa nem ameaça.',
      'Fala de algo que você realmente fez ou marcou.',
    ],
    doThis: [
      'Mesmo assim, se não reconhecer o assunto, não responda e confirme por outro caminho.',
      'Prefira resolver pelo aplicativo ou telefone oficial da empresa.',
    ],
    quiz: {
      message: 'Olá! Sua consulta está marcada para terça-feira às 9h. Responda 1 para confirmar ou 2 para remarcar.',
      isScam: false,
      explanation: 'Não pede dinheiro, senha, código nem clique em link. Se você marcou essa consulta, é provável que seja verdadeira.',
    },
    sources: [],
  },
]
