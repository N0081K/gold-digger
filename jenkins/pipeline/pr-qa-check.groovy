def github
String dockerImageName = "gold-digger-qa-check"

pipeline {
    agent {
        label "docker01"
    }

    libraries {
        lib("jenkins-pipes@master")
    }

    options {
        timeout(time: 1, unit: 'HOURS')
        ansiColor("gnome-terminal")
    }

    stages {
        stage("Load libraries and global variables") {
            steps {
                script {
                    def rootDir = pwd()
                    github = load "${rootDir}/jenkins/pipeline/_github.groovy"
                }
            }
        }

        stage("PR check") {
            steps {
                script {
                    String errorMessage = prCheck()

                    String messagePrefix = "<b>PR check:</b><BR>"
                    List<String> commentsURLToDelete = github.getCommentsURLToDelete(messagePrefix)
                    commentsURLToDelete.each {
                        github.deleteComment(it)
                    }

                    if (errorMessage) {
                        echo errorMessage
                        String formattedErrorMessage = messagePrefix + formatMessage(errorMessage)
                        github.sendCommentToGit(formattedErrorMessage)
                        error errorMessage
                    }
                }
            }
        }

        stage("Build Docker image") {
            steps {
                script {
                    sh "docker build --rm -t $dockerImageName --build-arg REQUIREMENTS=-qa-check -f Dockerfile ."
                }
            }
        }

        stage("Black check") {
            steps {
                script {
                    sh """
                        docker run --rm \
                            --name=${dockerImageName}-${env.BUILD_ID} \
                            --user=\$(id -u):\$(id -g) \
                            ${dockerImageName} \
                            black --check --color --diff --quiet .
                    """
                }
            }
        }

        stage("Ruff check") {
            steps {
                script {
                    sh """
                        docker run --rm \
                            --name=${dockerImageName}-${env.BUILD_ID} \
                            --user=\$(id -u):\$(id -g) \
                            ${dockerImageName} \
                            ruff --no-cache --quiet .
                    """
                }
            }
        }

        stage("Remove Docker image") {
            steps {
                script {
                    sh "docker rmi $dockerImageName"
                }
            }
        }
    }

    post {
        cleanup {
            cleanWs(disableDeferredWipeout: true, deleteDirs: true)
        }
    }
}

static String formatMessage(String message) {
    message = message.replaceAll("\n", "<BR>")
    message = message.replaceAll("\r", "<BR>")
    message = message.replaceAll("\t", "&nbsp; &nbsp; ")
    message = message.replaceAll("\"", "&quot;")

    return message
}
