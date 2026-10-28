pipeline {
    agent any

    environment {
        UV_PROJECT_ENVIRONMENT = '/tmp/uv_env'
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout & Setup') {
            steps {
                echo '=== Sincronizando repositorio e dependencias via uv ==='
                sh 'uv sync --all-packages'
            }
        }

        stage('Qualidade de Codigo & Seguranca') {
            parallel {
                stage('Lint & Estilo') {
                    steps {
                        echo '=== Executando verificacao de sintaxe e estilo ==='
                        sh 'uv run flake8 packages services --max-line-length=100 --ignore=E203,W503 --exclude=.venv,__pycache__'
                    }
                }
                stage('Analise Estatica SAST') {
                    steps {
                        echo '=== Executando auditoria de seguranca SAST com Bandit ==='
                        sh 'uv run bandit -r packages services -x .venv,tests -ll'
                    }
                }
                stage('Auditoria de Vulnerabilidades') {
                    steps {
                        echo '=== Executando auditoria de CVEs nas dependencias ==='
                        sh 'uv run pip-audit --ignore-vuln=PYSEC-0000'
                    }
                }
            }
        }

        stage('Testes Unitarios & Cobertura') {
            steps {
                echo '=== Executando testes unitarios com cobertura minima de 80% ==='
                sh 'uv run pytest packages services -m "not integration" --cov=packages --cov=services --cov-report=term-missing --cov-fail-under=80 -q'
            }
        }

        stage('Testes do Frontend & Acessibilidade') {
            steps {
                dir('web') {
                    echo '=== Compilando frontend e rodando testes vitest (WCAG 2.2 AA) ==='
                    sh 'npm test -- --run'
                    sh 'npm run build'
                }
            }
        }

        stage('Gate Cientifico de Regressao F1') {
            steps {
                echo '=== Validando Gate Cientifico Automatizado (F1 >= 0.92 na cascata) ==='
                // Exit 2 while the test split has no real samples: the gate never passes on made-up data.
                sh 'uv run python -m research_runner --threshold-f1 0.92'
            }
        }

        stage('Build das Imagens Docker') {
            when {
                branch 'main'
            }
            steps {
                echo '=== Compilando imagens Docker para producao ==='
                // Compose requires POSTGRES_PASSWORD; it comes from the Jenkins credential, never from the repo.
                withCredentials([string(credentialsId: 'verifica-postgres-password', variable: 'POSTGRES_PASSWORD')]) {
                    sh 'docker compose -f infra/docker-compose.prod.yml build'
                }
            }
        }
    }

    post {
        always {
            cleanWs deleteDirs: true, notFailBuild: true
        }
        success {
            echo 'Pipeline de CI/CD do Verifica AI concluido com sucesso! Gate F1 >= 0.92 aprovado.'
        }
        failure {
            echo 'Falha detectada no pipeline de CI/CD. Verifique os logs das etapas anteriores.'
        }
    }
}
