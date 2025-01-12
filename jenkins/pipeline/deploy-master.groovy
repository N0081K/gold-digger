def release

pipeline {
    agent {
        label "docker01"
    }

    libraries {
        lib("jenkins-pipes@master")
    }

    options {
        ansiColor("XTerm")
        timestamps()
    }

    parameters {
        booleanParam(
            name: "FEATURE_RELEASE",
            defaultValue: false,
            description: "Whether feature or bug fix should be released."
        )
        string(
            name: "RELEASE_VERSION",
            defaultValue: "",
            description: "Specify release version number. (FEATURE_RELEASE will be ignored)"
        )
    }

    environment {
        BRANCH_NAME = env.GIT_BRANCH.replaceFirst("origin/", "")
    }

    stages {
        stage("Determine next app version") {
            steps {
                script {
                    release = determineNextAppVersion {
                        prerelease = false
                        projectNameGithub = "gold-digger"
                        releaseVersion = params.RELEASE_VERSION
                        featureRelease = params.FEATURE_RELEASE
                        slackChannel = "python-alerts"
                        targetBranch = "master"
                        hasProjectPrerelease = false
                    }
                    env.APP_VERSION = release.newVersion
                }
            }
        }

        stage("Build Docker image") {
            steps {
                script {
                    dockerBuild env.BRANCH_NAME, "golddigger"
                }
            }
        }

        stage("Deploy API") {
            steps {
                script {
                    withCredentials([file(credentialsId: "gke-roihunter-master-autopilot-service-account", variable: "service_account"), file(credentialsId: "gke-roihunter-master-autopilot", variable: "kube_config")]) {
                        sh '''
                        gcloud auth activate-service-account gke-roihunter-master@roihunter-master.iam.gserviceaccount.com --key-file="$service_account"
                        sed -i "s/\\$BUILD_NUMBER/$BUILD_NUMBER/g" kubernetes/gold-digger-api-deployment.yaml
                        sed -i "s/\\$BUILD_NUMBER/$BUILD_NUMBER/g" kubernetes/gold-digger-cron-deployment.yaml
                        sed -i "s/\\$APP_VERSION/$APP_VERSION/g" kubernetes/gold-digger-api-deployment.yaml
                        sed -i "s/\\$APP_VERSION/$APP_VERSION/g" kubernetes/gold-digger-cron-deployment.yaml
                        kubectl --kubeconfig="$kube_config" apply -Rf kubernetes/
                        kubectl --kubeconfig="$kube_config" rollout status deployment/gold-digger-deployment --timeout 10m
                        kubectl --kubeconfig="$kube_config" rollout status deployment/gold-digger-cron-deployment --timeout 10m
                        '''
                    }
                }
            }
        }

        stage("Do GitHub release") {
            steps {
                script {
                    doGitHubRelease({}, release)
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
