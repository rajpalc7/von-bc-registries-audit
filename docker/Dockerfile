FROM registry.access.redhat.com/ubi8/python-39:latest

# Change timezone to PST for convenience
ENV TZ=PST8PDT

# ========================================================================================================
# Install go-crond (from https://github.com/BCDevOps/go-crond)
#  - Adds some additional logging enhancements on top of the upstream project; 
#    https://github.com/webdevops/go-crond
#
# CRON Jobs in OpenShift:
#  - https://blog.danman.eu/cron-jobs-in-openshift/
# --------------------------------------------------------------------------------------------------------
ARG SOURCE_REPO=webdevops
ARG GOCROND_VERSION=21.5.0
ADD https://github.com/$SOURCE_REPO/go-crond/releases/download/$GOCROND_VERSION/go-crond-64-linux /usr/bin/go-crond

COPY ./docker/run.sh .
COPY ./docker/audit.conf .
COPY ./scripts ./scripts
RUN cd $HOME/scripts && pip install -r requirements.txt
RUN mkdir -p $HOME/scripts/export

USER root
# ========================================================================================================
# Perform operations that require root privilages here ...
# --------------------------------------------------------------------------------------------------------
RUN echo $TZ > /etc/timezone
RUN chmod +x /usr/bin/go-crond
RUN chmod +x ./run.sh
RUN chown default:root $HOME/scripts/export
# ========================================================================================================
USER 1001