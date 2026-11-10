// ReviewOps pipeline (baseline). Stages marked TODO are filled in during weeks 2-3.
pipeline {
  agent any
  options { timestamps(); disableConcurrentBuilds() }
  triggers { githubPush() }   // GitHub webhook -> "GitHub hook trigger for GITScm polling"
  parameters {
    booleanParam(name: 'DEPLOY', defaultValue: false,
                 description: 'Deploy to Kubernetes (enable once the cluster is reachable from Jenkins)')
  }
  environment {
    DOCKERHUB_USER = 'your-dockerhub-username'          // TODO: set your Docker Hub user
    IMAGE_REPO     = "${DOCKERHUB_USER}/reviewops"
    IMAGE_TAG      = "${env.BUILD_NUMBER}"
  }
  stages {
    stage('Checkout')   { steps { checkout scm } }

    stage('Unit tests') {
      steps { sh 'docker build --target unit-test -f app/Dockerfile .' }
    }

    stage('Eval gate') {   // fails the build if recall/false-positive thresholds are missed
      steps { sh 'docker build --target eval-gate -f app/Dockerfile .' }
    }

    stage('Build image') {
      steps {
        sh """docker build --target runtime --build-arg APP_VERSION=${IMAGE_TAG} \
              -t ${IMAGE_REPO}:${IMAGE_TAG} -t ${IMAGE_REPO}:latest -f app/Dockerfile ."""
      }
    }

    stage('Trivy scan') {   // report-only for now; change --exit-code to 1 to enforce
      steps {
        sh """docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
              image --exit-code 0 --severity HIGH,CRITICAL ${IMAGE_REPO}:${IMAGE_TAG}"""
      }
    }

    stage('Push image') {   // TODO (week 2): read these credentials from Vault instead
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
          sh 'echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin'
          sh "docker push ${IMAGE_REPO}:${IMAGE_TAG} && docker push ${IMAGE_REPO}:latest"
        }
      }
    }

    stage('Deploy canary') {
      when { expression { params.DEPLOY } }
      steps {
        sh "ansible-playbook ansible/deploy.yml -e deploy_mode=canary -e image_repo=${IMAGE_REPO} -e image_tag=${IMAGE_TAG}"
      }
    }

    stage('Canary eval') {   // TODO (week 3): reach the canary service (port-forward/NodePort) and run:
      when { expression { params.DEPLOY } }   //   python3 benchmark/run_benchmark.py --url <canary-url>
      steps { echo 'TODO: run benchmark against the canary' }
    }

    stage('Promote') {
      when { expression { params.DEPLOY } }
      steps {
        sh "ansible-playbook ansible/deploy.yml -e deploy_mode=promote -e image_repo=${IMAGE_REPO} -e image_tag=${IMAGE_TAG}"
      }
    }
  }
  post {
    failure {
      script {
        if (params.DEPLOY) {   // never leave a failed canary running
          sh 'ansible-playbook ansible/deploy.yml -e deploy_mode=discard || true'
        }
      }
    }
  }
}
