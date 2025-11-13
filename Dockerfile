# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    INFRA_AGENT_CONFIG=/etc/infrastructure_agent/config.yml \
    INFRA_AGENT_WORKDIR=/var/lib/infrastructure_agent \
    INFRA_AGENT_LOG_DIR=/var/log/infrastructure_agent

WORKDIR /opt/infrastructure_agent

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY infrastructure_agent/ infrastructure_agent/
RUN mkdir -p /etc/infrastructure_agent
COPY config/infrastructure_agent.yml ${INFRA_AGENT_CONFIG}

RUN python -m compileall infrastructure_agent \
    && groupadd --system agent \
    && useradd --system --gid agent --home ${INFRA_AGENT_WORKDIR} --shell /usr/sbin/nologin agent \
    && mkdir -p ${INFRA_AGENT_WORKDIR} ${INFRA_AGENT_LOG_DIR} \
    && chown -R agent:agent ${INFRA_AGENT_WORKDIR} ${INFRA_AGENT_LOG_DIR} /opt/infrastructure_agent /etc/infrastructure_agent

VOLUME ["/var/lib/infrastructure_agent", "/var/log/infrastructure_agent"]

EXPOSE 8020

USER agent

ENTRYPOINT ["python", "-m", "infrastructure_agent.cli"]
CMD ["--config", "/etc/infrastructure_agent/config.yml", "--dashboard"]
