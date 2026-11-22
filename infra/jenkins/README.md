# Jenkins local

Roda o `Jenkinsfile` do repositório num Jenkins em Docker, para ver o pipeline no **Pipeline Graph View** (por exemplo, para a figura do artigo).

- O Jenkins tem o próprio Docker (`dind`). O estágio de integração sobe Postgres e Redis lá dentro, sem tocar nos containers da sua máquina.
- O job `verifica-ai` clona o repositório montado em `/repo` e constrói **o último commit** da branch. Mudanças sem commit não entram.
- A interface fica só em `http://localhost:8080`, sem login.
- A única credencial do pipeline que roda fora da `main` é a senha do Postgres de CI. Ela é gerada a cada subida e não fica em arquivo. O estágio de build das imagens só roda na `main` e não é executado aqui.

## Subir e rodar

```powershell
$env:VERIFICA_CI_POSTGRES_PASSWORD = [guid]::NewGuid().ToString("N")
$env:VERIFICA_CI_BRANCH = git branch --show-current
docker compose -f infra/jenkins/docker-compose.yml up -d --build
```

Depois abra `http://localhost:8080/job/verifica-ai/` e clique em **Build Now**. Ao fim, o grafo fica em **Stages** (`/job/verifica-ai/<número>/stages/`).

## Desligar

```powershell
docker compose -f infra/jenkins/docker-compose.yml down
```

Com `down -v`, o histórico de builds e o cache do Docker interno também são apagados.
