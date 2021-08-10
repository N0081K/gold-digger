def github

pipeline {
    agent {
        label "docker01"
    }

    libraries {
        lib("jenkins-pipes@master")
    }

    options {
        timeout(time: 1, unit: 'HOURS')
        ansiColor colorMapName: "gnome-terminal"
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

        stage("Coala") {
            steps {
                sh 'docker run --rm -t -v "$(pwd):/app" --workdir=/app coala/base:0.11 coala -d bears --non-interactive --no-color'
            }
        }
    }

    post {
        always {
            cleanWs()
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
