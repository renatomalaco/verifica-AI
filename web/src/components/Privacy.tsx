import { useEffect, useRef, useState, type ReactNode } from 'react'
import { usePreferences } from '../prefs/context'
import { DEFAULT_PREFERENCES } from '../prefs/preferences'
import { BackIcon } from './Icons'

interface PrivacyProps {
  onBack: () => void
}

// Everything here must match what the backend actually does:
// migrations/0001 (what is stored), domain/quota.py and settings (limits and retention).
export function Privacy({ onBack }: PrivacyProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)
  const [cleared, setCleared] = useState(false)
  const { replace } = usePreferences()

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  const clearDevice = () => {
    try {
      Object.keys(window.localStorage)
        .filter((k) => k.startsWith('vf.'))
        .forEach((k) => window.localStorage.removeItem(k))
    } catch {
      // No storage: nothing was saved.
    }
    replace({ ...DEFAULT_PREFERENCES })
    setCleared(true)
  }

  return (
    <article className="app-main" aria-labelledby="privacidade-titulo">
      <button type="button" className="btn btn-quiet align-start" onClick={onBack}>
        <BackIcon size={22} />
        Voltar
      </button>

      <div className="stack">
        <h1 className="title-l" id="privacidade-titulo" ref={headingRef} tabIndex={-1}>
          Como o Verifica cuida dos seus dados
        </h1>
        <p className="text-muted">
          O Verifica é um projeto de pesquisa (TCC). Para medir se a ferramenta funciona bem, alguns dados das análises são
          registrados, sempre de forma anônima: nada fica ligado a você.
        </p>
      </div>

      <PrivacySection title="O que não é guardado">
        <ul className="bullet-list bullet-list--ok">
          <li>O texto, o link ou o print que você colou.</li>
          <li>Seu nome, telefone, CPF ou qualquer cadastro. O Verifica não pede conta.</li>
          <li>Seu endereço de internet (IP) junto com as análises.</li>
        </ul>
      </PrivacySection>

      <PrivacySection title="O que fica registrado, e por quê">
        <p>De cada análise, fica só:</p>
        <ul className="bullet-list bullet-list--ok">
          <li>o tipo (mensagem, link ou foto) e o resultado (golpe, cuidado, seguro ou sem certeza);</li>
          <li>quanto tempo cada etapa da investigação levou, e a data e hora;</li>
          <li>
            uma <strong>impressão digital</strong> do conteúdo: um código calculado a partir dele, que não guarda o texto. Ela
            serve para reconhecer quando o mesmo golpe aparece de novo.
          </li>
        </ul>
        <p>
          <strong>Para que serve:</strong> esses registros anônimos alimentam as métricas do modo pesquisa do TCC, como o tempo
          de resposta e a proporção de cada tipo de resultado. Assim dá para comprovar se a ferramenta é rápida e confiável,
          sem identificar quem usou.
        </p>
      </PrivacySection>

      <PrivacySection title="Durante a investigação">
        <ul className="bullet-list bullet-list--ok">
          <li>
            Antes de o texto ir para o serviço de inteligência artificial, dados como CPF, cartão, telefone, e-mail e senhas são
            escondidos.
          </li>
          <li>Os links são abertos num navegador isolado, no servidor do Verifica, e nunca no seu aparelho.</li>
        </ul>
      </PrivacySection>

      <PrivacySection title="O limite do “Me explica”">
        <p>
          Para contar quantas explicações já foram pedidas, o navegador guarda um código aleatório, que não diz quem você é. Os
          contadores se apagam sozinhos: o do dia em até 2 dias, o do mês em até 32 dias. O endereço de internet é usado só para
          evitar abuso e fica guardado por no máximo 1 hora.
        </p>
      </PrivacySection>

      <PrivacySection title="Neste aparelho">
        <p>
          Os ajustes de leitura, o tutorial já visto e o progresso das lições ficam salvos só no seu navegador e não são enviados
          para ninguém.
        </p>
        {cleared ? (
          <p className="note" role="status">
            Pronto. Os dados deste aparelho foram apagados.
          </p>
        ) : (
          <button type="button" className="btn btn-outline" onClick={clearDevice}>
            Apagar dados deste aparelho
          </button>
        )}
      </PrivacySection>

      <p className="text-muted text-small">
        O Verifica segue os princípios da Lei Geral de Proteção de Dados (Lei 13.709/2018): usar só o necessário, com
        finalidade clara, e de forma anônima.
      </p>
    </article>
  )
}

function PrivacySection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card stack stack-roomy">
      <h2 className="title-m">{title}</h2>
      {children}
    </section>
  )
}
