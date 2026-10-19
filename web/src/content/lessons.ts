// Content for "Aprenda a se proteger". General, verifiable guidance:
// no made-up statistics or cases.

export interface Lesson {
  id: string
  title: string
  summary: string
  howItWorks: string
  signs: string[]
  doThis: string[]
  quiz: {
    message: string
    isScam: boolean
    explanation: string
  }
}

export const GOLDEN_RULES: string[] = [
  'Pressa é sinal de golpe. Quem é de verdade espera você confirmar.',
  'Ninguém de confiança pede senha, código ou token por mensagem ou ligação.',
  'Confirme por outro caminho: ligue você mesmo para o número que já conhece.',
  'Não clique em links de mensagens que você não esperava.',
  'Na dúvida, confira no Verifica ou pergunte a alguém de confiança.',
]

export const LESSONS: Lesson[] = [
  {
    id: 'falso-parente',
    title: 'Golpe do falso parente',
    summary: 'Alguém finge ser da família, com número novo, e pede dinheiro.',
    howItWorks:
      'O golpista manda mensagem dizendo que é seu filho, neto ou outro parente e que trocou de número. Pouco depois, pede um Pix ou o pagamento de uma conta com urgência.',
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
  },
  {
    id: 'central-banco',
    title: 'Falsa central do banco',
    summary: 'Ligação ou SMS fingindo ser do banco para pegar senha ou dinheiro.',
    howItWorks:
      'Alguém liga ou manda SMS avisando de uma compra suspeita no seu cartão. Para "proteger" a conta, pede sua senha, um código, que você instale um aplicativo ou transfira o dinheiro para uma "conta segura".',
    signs: [
      'Pede senha, código que chegou por SMS ou número do token.',
      'Pede para instalar um aplicativo ou transferir dinheiro para "proteger" a conta.',
      'O SMS manda você ligar para um número que está na própria mensagem.',
    ],
    doThis: [
      'Desligue. Não continue a conversa.',
      'Ligue você mesmo para o número que está no verso do seu cartão ou no aplicativo do banco.',
      'Lembre: o banco não pede senha nem pede para você transferir dinheiro para proteger a conta.',
    ],
    quiz: {
      message: 'BANCO: Compra de R$ 2.890,00 aprovada no seu cartão. Não reconhece? Ligue agora para 0800 000 0000.',
      isScam: true,
      explanation: 'O número para ligar está na própria mensagem, que é como o golpe começa. Confira a compra no aplicativo do banco ou ligue para o número do verso do cartão.',
    },
  },
  {
    id: 'links-falsos',
    title: 'Links e sites falsos',
    summary: 'Páginas que imitam banco, governo ou loja para roubar seus dados.',
    howItWorks:
      'A mensagem traz um link para um site muito parecido com o verdadeiro. Lá, pede senha, dados do cartão ou CPF. Às vezes ameaça bloquear algo se você não "regularizar" logo.',
    signs: [
      'O endereço tem letras trocadas ou palavras a mais, como "atualiza", "regulariza" ou "seguro".',
      'Promoção boa demais ou ameaça de bloqueio com prazo curto.',
      'O site pede senha ou dados do cartão logo de cara.',
    ],
    doThis: [
      'Não clique no link da mensagem.',
      'Abra o aplicativo oficial ou digite você mesmo o endereço que já conhece.',
      'Antes de abrir, cole o link no Verifica para conferir.',
    ],
    quiz: {
      message: 'Seu CPF será bloqueado hoje. Regularize em gov-br-regulariza.com para evitar multa.',
      isScam: true,
      explanation: 'Ameaça com prazo curto e um endereço que imita o do governo. Sites oficiais do governo terminam em .gov.br, sem palavras a mais no meio.',
    },
  },
  {
    id: 'codigo-whatsapp',
    title: 'Código do WhatsApp',
    summary: 'Pedem o código que chegou por SMS para roubar sua conta.',
    howItWorks:
      'O golpista tenta entrar no WhatsApp com o seu número. O aplicativo manda um código para o seu celular, e ele pede esse código fingindo ter mandado por engano ou ser de uma empresa.',
    signs: [
      'Alguém pede um código de 6 números que chegou para você.',
      'Diz que mandou o código "por engano".',
      'Fala em nome de uma loja, pesquisa ou sorteio.',
    ],
    doThis: [
      'Nunca passe códigos que chegarem por SMS, para ninguém.',
      'Ative a confirmação em duas etapas no WhatsApp: Configurações, depois Conta, depois Confirmação em duas etapas.',
      'Se perder o acesso, avise seus contatos por outro meio para não caírem no golpe.',
    ],
    quiz: {
      message: 'Oi! Te mandei um código de 6 números por engano. Pode me passar, por favor?',
      isScam: true,
      explanation: 'Esse código dá acesso à sua conta. Quem tiver ele pode falar com seus contatos fingindo ser você.',
    },
  },
  {
    id: 'pix-boleto',
    title: 'Pix, boletos e QR Code',
    summary: 'Cobranças falsas que mandam o dinheiro para a pessoa errada.',
    howItWorks:
      'Chega um boleto ou um QR Code com desconto ou cobrança urgente. Na hora de pagar, o dinheiro vai para a conta do golpista, e não para a empresa.',
    signs: [
      'Boleto ou cobrança que chegou por mensagem, sem você esperar.',
      'O nome de quem vai receber, na tela do banco, não é o da empresa.',
      'Desconto grande para pagar "só hoje".',
    ],
    doThis: [
      'Antes de confirmar, leia o nome de quem vai receber na tela do banco.',
      'Pegue boletos no site ou aplicativo oficial da empresa.',
      'Configure no aplicativo do banco um limite menor para Pix à noite.',
    ],
    quiz: {
      message: 'Conta de luz com 50% de desconto para pagamento hoje! Pague pelo boleto em anexo.',
      isScam: true,
      explanation: 'Desconto grande e prazo curto, num boleto que chegou por mensagem. Pegue a conta no site ou aplicativo da companhia de luz.',
    },
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
  },
]

export function lessonSpeechText(lesson: Lesson): string {
  return [lesson.title, lesson.howItWorks, 'Sinais de alerta:', ...lesson.signs, 'O que fazer:', ...lesson.doThis].join(' ')
}

// Maps the verdict category to the lesson explaining that kind of scam.
const LESSON_BY_CATEGORY: Record<string, string> = {
  coercao_afetiva: 'falso-parente',
  urgencia: 'falso-parente',
  ameaca_financeira: 'central-banco',
  brand_spoofing: 'links-falsos',
  blacklist_feed: 'links-falsos',
  embedded_phishing_link: 'links-falsos',
  antibot_challenge: 'links-falsos',
}

export function lessonForCategory(category: string | null | undefined): string | null {
  return (category && LESSON_BY_CATEGORY[category]) || null
}

const PROGRESS_KEY = 'vf.lessons'

export function loadLessonProgress(): string[] {
  try {
    const raw = JSON.parse(window.localStorage.getItem(PROGRESS_KEY) ?? '[]')
    return Array.isArray(raw) ? raw.filter((id) => LESSONS.some((l) => l.id === id)) : []
  } catch {
    return []
  }
}

export function saveLessonProgress(ids: string[]): void {
  try {
    window.localStorage.setItem(PROGRESS_KEY, JSON.stringify(ids))
  } catch {
    // No storage: progress lasts only for this visit.
  }
}
