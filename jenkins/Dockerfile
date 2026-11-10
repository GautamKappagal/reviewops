# Jenkins with the tools our pipeline shells out to: docker CLI, ansible, kubectl, python3.
FROM jenkins/jenkins:lts-jdk17
USER root
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends \
      docker.io python3 python3-pip ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --break-system-packages ansible kubernetes \
    && ansible-galaxy collection install kubernetes.core -p /usr/share/ansible/collections
RUN curl -fsSL "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/${TARGETARCH:-amd64}/kubectl" \
      -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
USER jenkins
