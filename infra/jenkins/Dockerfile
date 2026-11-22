# Local Jenkins that runs the repository's Jenkinsfile as is: uv, Node, the Docker CLI with
# compose, and the OCR libraries the image-extractor tests load.
FROM jenkins/jenkins:lts-jdk21

# Root on purpose: the Jenkinsfile runs `npx playwright install --with-deps`, which calls apt-get.
# This Jenkins only listens on 127.0.0.1 and builds this repository.
USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por libzbar0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker:27-cli /usr/local/libexec/docker/cli-plugins/docker-compose \
     /usr/local/libexec/docker/cli-plugins/docker-compose
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# The job clones the bind-mounted repository, owned by another user.
RUN git config --system --add safe.directory '*'

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY casc.yaml /casc/casc.yaml

ENV CASC_JENKINS_CONFIG=/casc/casc.yaml \
    JAVA_OPTS="-Xmx768m -Djenkins.install.runSetupWizard=false -Dhudson.plugins.git.GitSCM.ALLOW_LOCAL_CHECKOUT=true"
