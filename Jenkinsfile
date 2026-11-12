// Verifica AI CI/CD (R7). Every shell step calls a command that also runs on a developer
// machine; the Python matrix and the integration stage live in scripts/ci/.
pipeline {
    agent any

    options {
        timeout(time: 60, unit: 'MINUTES')
        // The integration stage binds fixed loopback ports, so builds of this job run one at a time.
        disableConcurrentBuilds()
    }

    environment {
        // Per-build virtualenv inside the workspace: cleanWs removes it, and builds never share it.
        UV_PROJECT_ENVIRONMENT = "${WORKSPACE}/.venv"
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Preparar ambiente') {
            steps {
                // --frozen: install exactly uv.lock and fail if pyproject.toml drifted from it.
                sh 'uv sync --all-packages --frozen'
            }
        }

        stage('Auditoria de dependencias') {
            steps {
                // No ignores: a finding is fixed by upgrading. If one ever has to be ignored,
                // use --ignore-vuln <ID> with the reason written right next to it.
                sh 'uv run --no-sync pip-audit --skip-editable'
            }
        }

        stage('Python por componente') {
            matrix {
                axes {
                    axis {
                        name 'COMPONENT'
                        values 'packages/contracts',
                            'packages/observability',
                            'services/ai-gateway',
                            'services/image-extractor',
                            'services/research-runner',
                            'services/scan-orchestrator',
                            'services/threat-intel-sync',
                            'services/url-inspector'
                    }
                }
                stages {
                    stage('Lint, SAST e testes (cobertura >= 80%)') {
                        steps {
                            sh 'bash scripts/ci/python_component.sh "$COMPONENT"'
                        }
                    }
                }
            }
        }

        stage('Integracao (Docker)') {
            steps {
                withCredentials([
                    string(credentialsId: 'verifica-postgres-password', variable: 'POSTGRES_PASSWORD'),
                ]) {
                    sh 'bash scripts/ci/integration.sh'
                }
            }
        }

        stage('Frontend') {
            steps {
                dir('web') {
                    sh 'npm ci --no-audit --no-fund'
                    sh 'npm run lint'
                    sh 'npm test'
                    sh 'npm run build'
                    sh 'npx playwright install --with-deps chromium'
                    sh 'CI=1 npm run test:e2e'
                }
            }
        }

        stage('Gate cientifico F1') {
            steps {
                script {
                    // research_runner exit codes: 0 = F1 >= threshold, 1 = below, 2 = no real test samples.
                    int code = sh(
                        script: 'uv run --no-sync python -m research_runner --threshold-f1 0.92',
                        returnStatus: true
                    )
                    if (code == 2) {
                        error('Gate F1 (saida 2): o split de teste ainda nao tem amostras reais. ' +
                              'O pipeline fica vermelho de proposito ate a coleta do dataset ' +
                              '(services/research-runner/data/README.md): nenhum numero inventado passa pelo gate.')
                    }
                    if (code == 1) {
                        error('Gate F1 (saida 1): o F1 da cascata no split de teste ficou abaixo de 0.92. ' +
                              'Veja services/research-runner/reports/latest.json.')
                    }
                    if (code != 0) {
                        error("Gate F1: o research_runner terminou com a saida inesperada ${code}; veja o log acima.")
                    }
                }
            }
        }

        stage('Build das imagens Docker') {
            when {
                branch 'main'
            }
            steps {
                // Compose requires these secrets; they come from Jenkins credentials, never from the repo.
                withCredentials([
                    string(credentialsId: 'verifica-postgres-password', variable: 'POSTGRES_PASSWORD'),
                    string(credentialsId: 'verifica-auth-jwt-private-key', variable: 'AUTH_JWT_PRIVATE_KEY'),
                    string(credentialsId: 'verifica-auth-jwt-public-key', variable: 'AUTH_JWT_PUBLIC_KEY'),
                ]) {
                    sh 'docker compose -f infra/docker-compose.prod.yml build'
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/junit-*.xml'
            cleanWs deleteDirs: true, notFailBuild: true
        }
        success {
            echo 'Pipeline do Verifica AI verde: lint, seguranca, testes, integracao, frontend e gate F1 aprovados.'
        }
        failure {
            echo 'Pipeline vermelho: abra o primeiro estagio em vermelho e leia o fim do log dele.'
        }
    }
}
