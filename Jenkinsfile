#!/usr/bin/env groovy

def AWS_ECR_ID="412335208158.dkr.ecr.us-east-1.amazonaws.com"
def SERVICE="botanist"
def IMAGE_URI = "${AWS_ECR_ID}/${SERVICE}"
def GIT_REPO = "botanist"
def GIT_HASH

pipeline {
  agent {label 'docker'}
  parameters {
    string(name: 'slack_channel', defaultValue: '#eng-tooling-deploy', description: 'The slack channel (if any) to announce deploys to')
  }

  environment {
    GIT_HASH = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD | cut -c1-7').trim()
  }

  stages {
    stage('Build image') {
      steps {
        script {
          ecrUtils.loginToEcrHelper()
          GIT_HASH = sh(returnStdout: true, script: 'git rev-parse --short=7 HEAD | cut -c1-7').trim()
          timeout(time: 15, unit: 'MINUTES') {
            ansiColor('xterm') {
              sh "docker build --tag ${IMAGE_URI}:${env.BRANCH_NAME} --tag ${IMAGE_URI}:${GIT_HASH} --tag ${IMAGE_URI}:latest ."
            }
          }
        }
      }
    }
      
    stage('Push image to ECR') {
      when { branch 'main' }
      steps {
        sh "docker push ${IMAGE_URI}:${GIT_HASH}"
        sh "docker push ${IMAGE_URI}:latest"
      }
    }

    stage('Run image security') {
      steps {
        script {
          // Make sure correct image tag is used
          String imageTag = (env.BRANCH_NAME == 'main') ? 'latest' : GIT_HASH;

          // Run image security on built image
          sproutImageSecurity.runImageSecurity("infrastructure", "${IMAGE_URI}", imageTag)
        }
      }
    }
  }

  post {
    always {
      cleanWs()
    }
    failure {
      script {
        if (env.GIT_BRANCH == 'main') {
          slackSend(channel: params.slack_channel, message: "Failure: ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)", color: "danger")
        }
      }
    }
  }
}
