# Publicar o Verifica AI numa VM do Google Cloud

Guia para subir a stack de produção (`infra/docker-compose.prod.yml`) numa máquina virtual do Compute Engine, com HTTPS automático pelo Caddy.

**Onde fica cada coisa:**
- **Segredos** (senhas, chaves): no **Secret Manager** do Google Cloud. O script `infra/prod-compose.sh` lê os segredos na hora e os entrega só ao `docker compose`; nada com chave é gravado no disco da VM.
- **Configurações que não são segredo** (domínio, provedor de IA, preços): num `.env` na VM.
- **No repositório:** nenhum dos dois.

## 1. Criar o projeto e a VM (uma vez, pelo Cloud Shell)

No [console](https://console.cloud.google.com), com a organização selecionada, abra o **Cloud Shell** (ícone `>_` no topo). Ele já vem com o `gcloud` logado na sua conta. Cole os blocos abaixo em ordem.

**1.1 Descobrir os IDs da organização e da conta de faturamento** (a conta com os créditos do teste gratuito):

```bash
gcloud organizations list
gcloud billing accounts list
```

**1.2 Criar um projeto só para o Verifica AI.** Use um projeto próprio, e não `nonprod` ou `development`: assim o custo fica separado e, depois da banca, basta apagar o projeto para apagar tudo.

```bash
ORG=<ID da organização>
BILLING=<ID da conta de faturamento>
PROJECT=verifica-ai-tcc-$RANDOM   # o ID precisa ser único no Google Cloud
REGION=southamerica-east1
ZONE=southamerica-east1-a
echo "Projeto: $PROJECT"          # anote: os próximos passos usam esse ID

gcloud projects create $PROJECT --organization=$ORG --name="Verifica AI"
gcloud billing projects link $PROJECT --billing-account=$BILLING
gcloud config set project $PROJECT
gcloud services enable compute.googleapis.com secretmanager.googleapis.com
```

**1.3 Rede e firewall.** Organizações novas às vezes vêm sem a rede `default`.

```bash
gcloud compute networks list
# Só se a lista vier vazia:
gcloud compute networks create default --subnet-mode=auto

gcloud compute firewall-rules create verifica-ai-allow-web --network=default   --allow=tcp:80,tcp:443 --target-tags=verifica-ai-web
# SSH só pelo túnel do Google (IAP), nunca aberto para a internet:
gcloud compute firewall-rules create verifica-ai-allow-ssh-iap --network=default   --allow=tcp:22 --source-ranges=35.235.240.0/20 --target-tags=verifica-ai-web
```

**1.4 IP fixo e VM** (e2-standard-2, 8 GB, Ubuntu 24.04, em São Paulo):

```bash
gcloud compute addresses create verifica-ai-ip --region=$REGION
gcloud compute instances create verifica-ai-vm --zone=$ZONE --machine-type=e2-standard-2   --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud --boot-disk-size=40GB   --address=verifica-ai-ip --tags=verifica-ai-web --scopes=cloud-platform
gcloud compute addresses describe verifica-ai-ip --region=$REGION --format='value(address)'
```

O último comando mostra o **IP fixo**. Anote: o domínio vai apontar para ele.

**1.5 Permitir que a VM só leia os segredos** (o escopo `cloud-platform` libera a API; quem limita é este papel):

```bash
SA=$(gcloud compute instances describe verifica-ai-vm --zone=$ZONE --format='value(serviceAccounts[0].email)')
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA"   --role=roles/secretmanager.secretAccessor --condition=None
```

**1.6 Domínio.** No registrador, crie um registro **A** do domínio para o IP fixo. O HTTPS só sai depois que o DNS propagar, o que leva de minutos a algumas horas.

**Sem domínio próprio** (bom para testar ou demonstrar): use `<ip-com-traços>.sslip.io`, por exemplo `34-95-10-20.sslip.io`. Esse nome já aponta para o IP, sem cadastro, e o Caddy consegue o certificado do mesmo jeito.

**Se algum comando falhar por política da organização** (por exemplo, `constraints/compute.vmExternalIpAccess`), a mensagem diz qual restrição bloqueou. Ela se ajusta em **IAM e administrador → Políticas da organização**, só para este projeto.

## 2. Preparar a VM

Do Cloud Shell, entre na VM pelo túnel do Google:

```bash
gcloud compute ssh verifica-ai-vm --zone=$ZONE --tunnel-through-iap
```

Já dentro da VM:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER   # saia e entre de novo no SSH para valer
git clone https://github.com/renatomalaco/verifica-AI.git
cd verifica-AI
gcloud --version                # já vem nas imagens Ubuntu do Google Cloud
```

Se o repositório for privado, o `git clone` pede usuário e senha: use o seu usuário do GitHub e, como senha, um *personal access token* (GitHub → Settings → Developer settings), só com leitura do repositório.

## 3. Guardar os segredos no Secret Manager

Ainda no **Cloud Shell**, com o mesmo projeto. Os segredos aleatórios e as chaves da área de pesquisa são gerados ali mesmo e vão direto para o cofre, **sem aparecer na tela nem passar pelo seu computador**:

```bash
new_secret() { gcloud secrets create "$1" --replication-policy=automatic --data-file=- ; }

for n in POSTGRES_PASSWORD GRAFANA_ADMIN_PASSWORD DEVICE_TOKEN_SECRET; do
  python3 -c "import secrets; print(secrets.token_urlsafe(32), end='')" | new_secret $n
done

# Par de chaves Ed25519 da área de pesquisa (mesmo formato do research_cli keygen)
openssl genpkey -algorithm ed25519 -out /tmp/k.pem
openssl pkey -in /tmp/k.pem -outform DER | tail -c 32 | base64 -w0 | new_secret AUTH_JWT_PRIVATE_KEY
openssl pkey -in /tmp/k.pem -pubout -outform DER | tail -c 32 | base64 -w0 | new_secret AUTH_JWT_PUBLIC_KEY
shred -u /tmp/k.pem

# A chave do Gemini é colada sem aparecer na tela
read -rs -p "Cole a GEMINI_API_KEY e tecle Enter: " K; echo
printf '%s' "$K" | new_secret GEMINI_API_KEY; unset K

gcloud secrets list
```

**Dicas:**
- Para produção, vale criar no Google AI Studio uma **chave nova, só para o site**, em vez de reusar a do seu `.env`. Assim, trocar uma não derruba a outra.
- **Ver a senha do Grafana depois:** `gcloud secrets versions access latest --secret=GRAFANA_ADMIN_PASSWORD`.
- **Trocar uma chave:** `printf '%s' "<novo valor>" | gcloud secrets versions add <NOME> --data-file=-`, e depois rodar de novo o `up -d` do passo 5.

## 4. Configurações que não são segredo

Na VM, crie `verifica-AI/.env` (`nano .env`):

```text
PUBLIC_DOMAIN=seu-dominio.com.br
ACME_EMAIL=e-mail para o Let's Encrypt avisar sobre o certificado
AI_PROVIDER=gemini
EXPLAIN_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_DEEP_MODEL=gemini-3.8-flash
# Opcionais
GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite
GEMINI_PRICE_INPUT_USD_PER_1M=
GEMINI_PRICE_OUTPUT_USD_PER_1M=
GEMINI_PRICE_DATE=
```

A triagem usa três modelos:

- `GEMINI_MODEL`: o rápido (Flash-Lite). Responde primeiro e também faz o "Me explica".
- `GEMINI_FALLBACK_MODEL`: a reserva do rápido, tentada uma vez quando ele falha (503 ou demora). Prefira outra versão do Lite: em 2026-11-21 o 3.8 Flash passou minutos respondendo 503 enquanto os Lite respondiam em menos de 2 s.
- `GEMINI_DEEP_MODEL`: o mais forte. Confirma os casos em dúvida e todo resultado que seria SEGURO. Se ele falhar, a dúvida fica como CUIDADO e o SEGURO vira INCONCLUSIVO.

`GEMINI_MODEL` e `GEMINI_DEEP_MODEL` são obrigatórios e não têm valor padrão no código: o Google aposenta modelos, e um nome antigo faz toda chamada responder 404 (por exemplo, o `gemini-2.5-flash`). Use nomes fixos, nunca os `-latest`, para o estudo saber qual modelo rodou. Quando um modelo sair do ar, troque aqui e rode de novo o `up -d` do passo 5.

Sem os três preços, o estudo marca o Modo 2 como não executado, em vez de estimar um custo.

## 5. Subir

Todo comando de produção passa pelo script, porque o compose exige os segredos até para mostrar logs:

```bash
bash infra/prod-compose.sh up -d --build
bash infra/prod-compose.sh ps
```

Se faltar um secret ou a permissão, o script para e diz qual. As migrations rodam sozinhas antes do orchestrator subir. A primeira construção leva vários minutos (Chromium, Tesseract e o modelo SigLIP). Depois, abra `https://<seu domínio>`.

## 6. Conta da área de pesquisa

```bash
bash infra/prod-compose.sh exec scan-orchestrator python -m scan_orchestrator.research_cli invite --email <seu e-mail> --role admin
```

O comando mostra um link de uso único para criar a senha.

## 7. Observabilidade (só para o autor)

Jaeger e Grafana escutam apenas dentro da VM. Para abrir no seu navegador, crie um túnel SSH a partir do seu computador:

```bash
gcloud compute ssh verifica-ai-vm --zone southamerica-east1-a --tunnel-through-iap -- -L 16686:localhost:16686 -L 3000:localhost:3000
```

Depois, Jaeger fica em `http://localhost:16686` e Grafana em `http://localhost:3000` (usuário `admin`, senha do secret `GRAFANA_ADMIN_PASSWORD`).

## 8. Atualizar e desligar

- **Nova versão:** `git pull` e `bash infra/prod-compose.sh up -d --build`. Se a VM tiver dificuldade para baixar do Docker Hub, construa uma imagem por vez (`bash infra/prod-compose.sh build <serviço>`).
- **Conferir as imagens:** `SMOKE_COMPOSE="bash infra/prod-compose.sh" bash scripts/ci/smoke_images.sh` importa, dentro de cada imagem, o que ela roda. Deve terminar com `All production images import what they run.`
- **Logs:** `bash infra/prod-compose.sh logs -f scan-orchestrator`.
- **Memória:** cada container tem um teto de RAM e de CPU (`mem_limit` e `cpus` no compose), somando cerca de 7,3 GB dos 8 GB da VM. Depois do primeiro uso real, confira com `docker stats --no-stream`. Se um serviço viver encostado no teto, aumente o dele e diminua o de outro.
- **Para não gastar os créditos à toa:** pare a VM no console quando não estiver usando. O IP estático continua reservado, e ele custa algo enquanto a VM estiver parada.

## Limite desta proteção

O Secret Manager tira as chaves do disco, registra quem leu cada uma e facilita a troca. Mas, com os containers rodando, as chaves viram variáveis de ambiente deles: quem tiver acesso de administrador à VM consegue vê-las com `docker inspect`. Proteja o acesso SSH, que fica restrito à sua conta Google.
