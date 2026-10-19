"""Curated log-pattern library for Spark/AWS Glue failure signatures.

The library is *data*: add a LogPattern entry and detection works without
code changes. Status mapping follows §2.1:

- CONFIRMED — unambiguous error signature (stack trace class, explicit denial).
- PROBABLE — strong contextual signal (FetchFailed, executor lost, worker exit).
- POSSIBLE — weak/ambient signal worth flagging but not asserting.
"""

import re
from dataclasses import dataclass, field

from data_sentinel.core.contracts import FindingCategory, FindingStatus, Severity


@dataclass(frozen=True)
class LogPattern:
    pattern_id: str
    category: FindingCategory
    severity: Severity
    status: FindingStatus
    confidence: float
    title: str
    rationale: str
    regexes: tuple[re.Pattern[str], ...] = field(compare=False)
    suggested_actions: tuple[str, ...] = ()
    validation_steps: tuple[str, ...] = ()
    source: str = ""

    def matches(self, line: str) -> bool:
        return any(rx.search(line) for rx in self.regexes)


def _rx(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


LOG_PATTERNS: tuple[LogPattern, ...] = (
    LogPattern(
        pattern_id="oom-java",
        category=FindingCategory.OUT_OF_MEMORY,
        severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        confidence=0.95,
        title="OutOfMemoryError detectado no log",
        rationale=(
            "Assinatura inequívoca de java.lang.OutOfMemoryError indica que "
            "driver ou executor estourou o heap disponível."
        ),
        regexes=_rx(r"OutOfMemoryError"),
        suggested_actions=(
            "Aumentar spark.driver.memory ou spark.executor.memory",
            "Reduzir partições muito grandes / coletas para o driver",
            "Revisar skew de dados nas chaves de join/agregação",
        ),
        validation_steps=(
            "Reexecutar com mais memória e verificar se o OOM desaparece",
            "Inspecionar Spark UI (abas Executors/Stages) para o maior consumer",
        ),
        source="JVM throwable; comum em Spark/Glue",
    ),
    LogPattern(
        pattern_id="oom-container",
        category=FindingCategory.OUT_OF_MEMORY,
        severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        confidence=0.9,
        title="Container morto por limite de memória",
        rationale=(
            "YARN/K8s reporta container killed por exceder memória física — "
            "overhead do executor, não apenas heap JVM."
        ),
        regexes=_rx(
            r"container.*(killed|terminated).*(memory|oom)",
            r"memory used.*exceeds.*(max|physical memory)",
            r"Exit status (137|143)",
        ),
        suggested_actions=(
            "Aumentar spark.executor.memoryOverhead",
            "Reduzir spark.executor.cores para aliviar pressão de memória",
        ),
        validation_steps=(
            "Verificar memoryOverhead e métricas de container no ResourceManager",
        ),
        source="YARN ResourceManager diagnostics",
    ),
    LogPattern(
        pattern_id="executor-lost-retry",
        category=FindingCategory.EXECUTOR_LOSS,
        severity=Severity.HIGH,
        status=FindingStatus.PROBABLE,
        confidence=0.8,
        title="Executors perdidos / tasks esgotando retries",
        rationale=(
            "ExecutorLostFailure ou tasks falhando N vezes indicam perda de "
            "executors; causa raiz pode ser OOM, spot termination ou rede."
        ),
        regexes=_rx(
            r"ExecutorLostFailure",
            r"[Ll]ost task .*\d+(\.\d+)?.*(times|failures?)",
            r"executor .*(lost|removed|dead|terminated)",
            r"FetchFailedException",
        ),
        suggested_actions=(
            "Verificar causa da perda (OOM, preempção, rede) nos logs do executor",
            "Aumentar spark.task.maxFailures se falhas forem transitórias",
        ),
        validation_steps=(
            "Correlacionar timestamp com eventos de autoscaling/spot",
        ),
        source="Spark scheduler/YARN",
    ),
    LogPattern(
        pattern_id="disk-space",
        category=FindingCategory.DISK_SPACE,
        severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        confidence=0.9,
        title="Disco local esgotado",
        rationale=(
            "'No space left on device' é assinatura direta de disco local cheio "
            "(shuffle/spill/tmp)."
        ),
        regexes=_rx(r"No space left on device", r"Not enough disk space"),
        suggested_actions=(
            "Aumentar disco local dos workers (ou instâncias com instance store)",
            "Reduzir shuffle/partições ou habilitar shuffle external service",
        ),
        validation_steps=(
            "Verificar uso de disco nos nós durante o stage de shuffle",
        ),
        source="OS/filesystem",
    ),
    LogPattern(
        pattern_id="disk-spill-warn",
        category=FindingCategory.DATA_SKEW,
        severity=Severity.MEDIUM,
        status=FindingStatus.POSSIBLE,
        confidence=0.5,
        title="Spill excessivo para disco (possível skew)",
        rationale=(
            "WARNs de spill indicam dados não cabendo em memória; quando "
            "concentrados em poucas tasks, sugerem skew de chave."
        ),
        regexes=_rx(
            r"Spill(ing)? .* to disk",
            r"ExternalSorter.*spill",
            r"memory.*spill.*bytes",
        ),
        suggested_actions=(
            "Checar distribuição de chaves (skew) nas agregações/joins",
            "Considerar salting ou aumento de memória por task",
        ),
        validation_steps=(
            "Comparar input size por task na Spark UI",
        ),
        source="Spark shuffle/spill metrics",
    ),
    LogPattern(
        pattern_id="aws-access-denied",
        category=FindingCategory.PERMISSIONS,
        severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        confidence=0.9,
        title="Acesso negado em serviço AWS",
        rationale=(
            "AccessDenied/403 indica falta de permissão IAM (S3, Glue Catalog, "
            "Lake Formation) — erro determinístico de autorização."
        ),
        regexes=_rx(
            r"AccessDeniedException",
            r"Access Denied",
            r"Status Code: 403",
            r"not authorized to perform",
            r"Insufficient Lake Formation permission",
            r"User: arn:aws:.*is not authorized",
        ),
        suggested_actions=(
            "Revisar políticas IAM da role do job (S3, Glue, Lake Formation)",
            "Checar permissões de Lake Formation na tabela/banco alvo",
        ),
        validation_steps=(
            "Reproduzir a chamada com aws sts get-caller-identity + simulate-principal-policy",
        ),
        source="AWS IAM/Glue/Lake Formation error shapes",
    ),
    LogPattern(
        pattern_id="spark-exception",
        category=FindingCategory.UNKNOWN,
        severity=Severity.MEDIUM,
        status=FindingStatus.PROBABLE,
        confidence=0.6,
        title="Job abortado por SparkException",
        rationale=(
            "SparkException marca falha no job, mas a causa raiz exige "
            "contexto adicional (stage, task, exceção interna)."
        ),
        regexes=_rx(
            r"org\.apache\.spark\.SparkException",
            r"Job aborted due to stage failure",
            r"Application .* failed",
        ),
        suggested_actions=(
            "Localizar a primeira exceção interna (Caused by) no log",
            "Enviar event log do Spark para análise de stage/tarefa",
        ),
        validation_steps=(
            "Identificar o stage falho na Spark UI e a task raiz",
        ),
        source="Spark scheduler",
    ),
    LogPattern(
        pattern_id="iceberg-catalog",
        category=FindingCategory.CONFIGURATION,
        severity=Severity.MEDIUM,
        status=FindingStatus.CONFIRMED,
        confidence=0.85,
        title="Erro de catálogo/tabela Iceberg",
        rationale=(
            "Exceções do pacote org.apache.iceberg (NoSuchTable, Validation, "
            "CommitFailed) apontam para catálogo/tabela mal configurado."
        ),
        regexes=_rx(
            r"org\.apache\.iceberg\.exceptions",
            r"NoSuchTableException",
            r"Cannot find table",
            r"CommitFailedException",
        ),
        suggested_actions=(
            "Verificar nome fully-qualified (catalog.db.table)",
            "Conferir configuração do catalog Iceberg no Glue/Spark",
        ),
        validation_steps=(
            "Listar tabelas do catalog e comparar com o nome referenciado",
        ),
        source="Apache Iceberg exceptions",
    ),
    LogPattern(
        pattern_id="job-timeout",
        category=FindingCategory.TIMEOUT,
        severity=Severity.HIGH,
        status=FindingStatus.CONFIRMED,
        confidence=0.85,
        title="Timeout de job/stage",
        rationale=(
            "Mensagens de timeout explícito (job timeout, fetch wait, "
            "broadcast join timeout) indicam SLA ou espera excedida."
        ),
        regexes=_rx(
            r"[Tt]imed? ?out",
            r"TimeoutException",
            r"Job run timed out",
            r"exceeded.*(timeout|time limit)",
        ),
        suggested_actions=(
            "Verificar stages pendentes e estrangulamento de rede/IO",
            "Ajustar timeouts (spark.network.timeout, job timeout do Glue)",
        ),
        validation_steps=(
            "Comparar duração histórica do job com o timeout configurado",
        ),
        source="Spark/Glue timeout messages",
    ),
    LogPattern(
        pattern_id="python-worker",
        category=FindingCategory.EXECUTOR_LOSS,
        severity=Severity.MEDIUM,
        status=FindingStatus.PROBABLE,
        confidence=0.7,
        title="Falha de worker Python",
        rationale=(
            "Python worker exited unexpectedly / PythonException aponta erro "
            "em UDF/código Python — frequentemente memória ou exceção não tratada."
        ),
        regexes=_rx(
            r"Python worker exited unexpectedly",
            r"PythonException",
            r"pyspark.*(error|exception|worker)",
            r"org\.apache\.spark\.api\.python",
        ),
        suggested_actions=(
            "Capturar exceção interna do Python (Caused by / traceback)",
            "Aumentar memória do executor se UDF processa muitos dados",
        ),
        validation_steps=(
            "Executar a UDF localmente com a mesma partição de dados",
        ),
        source="PySpark daemon",
    ),
    LogPattern(
        pattern_id="missing-dependency",
        category=FindingCategory.DEPENDENCY,
        severity=Severity.MEDIUM,
        status=FindingStatus.CONFIRMED,
        confidence=0.85,
        title="Dependência/classe ausente no classpath",
        rationale=(
            "ClassNotFound/NoClassDefFound/ModuleNotFound indicam jar ou "
            "módulo não empacotado no job."
        ),
        regexes=_rx(
            r"ClassNotFoundException",
            r"NoClassDefFoundError",
            r"ModuleNotFoundError",
            r"ImportError",
        ),
        suggested_actions=(
            "Incluir o jar/módulo ausente (extra-jars, --additional-python-modules)",
            "Conferir versões de dependência compatíveis com o runtime",
        ),
        validation_steps=(
            "Reproduzir import localmente com o mesmo ambiente do job",
        ),
        source="JVM/Python import errors",
    ),
)
