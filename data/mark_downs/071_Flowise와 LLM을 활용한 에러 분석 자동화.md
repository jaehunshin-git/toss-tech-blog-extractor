# Flowise와 LLM을 활용한 에러 분석 자동화

**Date:** 2025년 5월 26일
**URL:** https://toss.tech/article/flowise-llm-error-analysis-automation

---

안녕하세요, 토스 코어 Teens Growth Silo의 서버 개발자 조민규입니다. 

서비스를 개발하다 보면 클라이언트의 호출에 의한 에러가 발생합니다. 클라이언트는 반환된 에러 메시지를 통해 발생 원인을 파악하고 해결할 수 있어야 하는데, 대부분의 경우 오류 메시지가 불친절하거나 혹은 보안적 이슈로 추상화되어 본질적인 원인 파악 및 해결에 어려움을 겪는 경우가 많죠. 이로 인해 불필요한 에러 원인 파악 및 해결을 위한 시간이 낭비되며 팀원 뿐만 아니라 팀의 전반적인 생산성을 낮출 수 있어요.

예를 들어 다음과 같이 에러 메시지에 충분한 정보가 제공되지 않으면 클라이언트는 원인을 파악하는 것이 불가능하며, 서버 에러의 스택 트레이스를 확인할 수 있다고 하더라도 이해하고 파악하기가 어려울 수 있습니다.

이를 개선하고자 요청 정보와 API 스펙 그리고 에러 스택 트레이스 등의 정보를 LLM에게 제공하여 문제가 발생한 원인을 분석하고, 어떻게 고쳐야 하는지 제안을 해주도록 하면 상황을 개선할 수 있을 것이라고 판단했습니다. 이를 실제로 적용하여, 팀 내부적으로 다음과 같이 활용하고 있어요.

## Flowise로 LLM 체인 구성하기

Flowise는 시각적인 인터페이스를 제공하는 오픈 소스 LLM\(대형 언어 모델\) 워크플로 빌더로, 코드를 작성하지 않고도 다양한 LLM 기반 애플리케이션을 쉽게 구성하고 배포할 수 있도록 설계되어 있어요. 이번에는 Flowise를 활용하여 다음과 같은 워크플로를 구성했습니다.

구성 요소는 다음과 같은데, 각각에 대해 자세히 살펴볼게요.

  * ChatOpenAI
  * API Loader
  * Structured Output Parser
  * Chat Prompt Template

### ChatOpenAI

관련 내용을 질의할 언어 모델\(Language Model\)을 설정합니다. 이번 케이스에서는 토스에서 자체적으로 생성한 모델인 toss-standard를 활용했어요. 

### API Loader

토스팀에서는 API 스펙 공유를 위해 Swagger를 활용하고 있으며, 따라서 다음의 두 의존성을 활용하고 있습니다.

  * `org.springdoc:springdoc-openapi-starter-webmvc-ui`: Swagger UI를 통해 브라우저에서 접속가능한 API 문서를 제공함
  * `org.springdoc:springdoc-openapi-starter-webmvc-api`: Swagger UI 없이 OpenAPI JSON/YAML 문서 형태로 제공함

LLM에게는 Json 형태의 스펙 문서가 제공되며, 클라이언트가 호출한 API가 구체적으로 어떠한 요청인지 식별하는데 활용돼요. 즉, Swagger를 통해 작성된 내용이 LLM의 메타데이터로 활용되는 것이죠. 따라서 관련 내용 역시 꼼꼼하게 작성해주면, 보다 정확한 답변을 얻을 수 있습니다.

### Structured Output Parser

Structured Output Parser는 LLM\(Large Language Model\)이 생성하는 텍스트를 특정 포맷\(구조화된 형식\)으로 맞추기 위해 사용하는 도구입니다. 보통 LLM은 자연어의 형태로 응답을 제공하는데, 특정한 형식에 맞추어 응답을 주기를 원할 때, Structured Output Parser를 활용할 수 있어요.

이번 프롬프트의 경우에는 4가지 key-value 쌍을 갖는 Json 형태로 응답이 제공되도록 활용되었습니다. 참고로 이 중에서 inference는 LLM으로 하여금 스스로 사고하도록 함으로써 추론의 정확도를 높이기 위해 활용됐어요.
    
    
    {
        "action": "처리 요청을 보냈던 행동"
        "reason": "에러가 발생한 이유"
        "guide": "에러 수정에 대한 가이드"
        "inference": "그렇게 action과 reason, guide를 추론한 이유"
    }

### Chat Prompt Template

프롬프트 작성의 경우에는 다음의 내용들을 고려했어요.

  * 고급 BE 개발자와 주니어 FE 및 PM으로 역할을 지정하여 서술하는 내용을 쉽게 이해 가능하도록 함
  * API 스펙을 요청의 메타데이터로 제공하여 도메인 언어로 에러가 발생한 상황을 소통할 수 있도록 함
  * API 스펙이 제공되지 않은 경우에 대비해, 클래스 및 메서드 정보를 바탕으로 추론을 보완하도록 함
  * 예시를 제공하고, 추론의 이유를 서술하도록 하여 정확도를 높일 수 있도록 함

    
    
    # 역할(Role)
    당신은 HTTP를 기반으로 통신하는 환경에서 Kotlin 개발 언어와 SpringBoot 프레임워크의 JVM 환경 기반 개발  경험을 7년 이상 보유한 서버 개발의 전문가입니다.
    
    # 목표(Goal)
    입력으로 주어지는 요청 URL과 요청 HttpMethod 그리고 에러의 StackTrace를 바탕으로, 해당 에러가 해당 서비스를 이용하는 사용자의 입장에서 어떤 상황에서 발생했고, 왜 발생했는지를 분석합니다. 상대방은 이제 막 개발을 시작한 1년차 FE 개발자와 새롭게 팀에 합류한 PM 기획자 둘이기 때문에, 최대한 이해하기 쉽게 내용을 설명해주어야 합니다.
    어떤 요청을 보낸 상황에서 문제가 발생했고, 에러가 생긴 원인은 무엇이고, 어떻게 해결할 수 있을지를 분석하여 이를 제공해주어야 합니다.
    
    # 가이드라인(Guidelines)
    해당 요청이 어떠한 요청인지는 API 관련 문서를 제공받을 것이므로, 제공된 문서에서 API URL과 Http Method를 바탕으로 매칭되는 정보를 찾고, 해당 부분에서 "summary"를 참조하면 됩니다. "summary"가 없는 경우에는 제공받은 StackTrace를 바탕으로 호출된 Service 클래스의 이름을 참조하면 됩니다. Service는 하나의 유스케이스를 표현하는 방식으로 클래스 이름이 작성되어 있기 때문입니다.
    에러가 발생한 원인은 입력으로 한 줄의 핵심 메시지인 errorMessage와 StackTrace를 제공받을 것이기 때문에 해당 내용을 분석하여 reason을 작성함으로써 PM이 왜 문제가 발생했는지를 인지할 수 있도록 하고, guide를 작성함으로써 FE 개발자가 어떻게 고치면 좋을지 제안해주면 됩니다.
    StackTrace와 함께, 서비스를 제공하는 서비스 이름(service)을 제공되므로, 해당 정보를 바탕으로 현재 하려고 하는 행동이 어떠한 것인지 StackTrace에 존재하는 클래스로부터도 확인할 수 있을 것입니다.
    두 정보를 바탕으로 분석에 필요한 내용들로 추리고, 남은 호출 클래스 및 메소드 정보들로 문제 상황을 분석하면 됩니다.
    
    # 입력 형식(Input Format)
    입력 데이터는 다음과 같이 구성되며, 각각은 다음을 의미합니다.
    company: 회사명
    service: 제공하는 서비스 이름
    httpMethod: HTTP 요청 메서드
    requestUrl: HTTP 요청 URL
    methodSignatures: 파라미터 시그니처 목록
    errorMessage: 에러가 발생한 핵심 메시지
    cause: 에러가 발생한 StackTrace
    
    여기서 methodSignatures는 다음의 4가지 정보를 갖는 methodSignature 정보의 List 자료구조를 문자열로 조합한 것입니다. 해당 데이터는 stackTrace를 바탕으로 문제가 왜 발생했는지, 어떻게 고치면 좋을지 추론하는데, 보다 많은 정보를 제공하여 오류를 최소화하기 위함입니다.
    className: 클래스 이름
    lineNumber: 라인 넘버
    parameters: name(파라미터 이름), type(타입) 정보를 갖는 클래스
    returnType: 반환 타입
    
    
    
    # 입력 예시(Input Example)
    1번 예시
    company: "toss"
    service: "teens"
    httpMethod: "get"
    requestUrl: "/apis/1.0/image-cards/{id}"
    methodSignatures: "[MethodSignatureInfo(className=im.toss.teens.invitation.adapter.cache.redis.UserShareKeyEncrypter, lineNumber=35, parameters=[ParameterInfo(name=decryptedArray, type=java.lang.String)], returnType=java.lang.String), MethodSignatureInfo(className=im.toss.teens.api.controller.imagecard.web.ImageCardController, lineNumber=29, parameters=[ParameterInfo(name=shareCode, type=java.lang.String)], returnType=im.toss.util.api.Response)]"
    cause:  "im.toss.teens.imagecard.adapter.persistence.ImageCardRepository$ImageCardNotFound: 존재하지 않는 이미지카드에요.
    at im.toss.teens.imagecard.adapter.persistence.ImageCardRepository$ImageCardNotFound.<clinit>(ImageCardRepository.kt)
    at im.toss.teens.imagecard.adapter.persistence.ImageCardRepository.findByIdOrThrow$lambda$0(ImageCardRepository.kt:27)
    at im.toss.teens.imagecard.adapter.persistence.ImageCardRepository.findByIdOrThrow(ImageCardRepository.kt:27)
    at im.toss.teens.home.adapter.outbound.persistence.config.RoutingDataSourceInterceptor.annotationRoutingDataSourceAnnotation(RoutingDataSourceInterceptor.kt:19)
    at im.toss.teens.imagecard.adapter.persistence.ImageCardRepository$$SpringCGLIB$$0.findByIdOrThrow(<generated>)
    at im.toss.teens.imagecard.application.services.GetImageCardService.execute(GetImageCardService.kt:34)
    at im.toss.teens.api.controller.imagecard.web.ImageCardController.getImageCard(ImageCardController.kt:47)
    at im.toss.teens.api.controller.imagecard.web.ImageCardController$$SpringCGLIB$$0.getImageCard(<generated>)
    "
    
    2번 예시
    company: "toss"
    service: "teens"
    httpMethod: "get"
    requestUrl: "/apis/1.0/card/images-cards"
    methodSignatures: "[MethodSignatureInfo(className=im.toss.teens.invitation.adapter.cache.redis.UserShareKeyEncrypter, lineNumber=35, parameters=[ParameterInfo(name=decryptedArray, type=java.lang.String)], returnType=java.lang.String), MethodSignatureInfo(className=im.toss.teens.api.controller.imagecard.web.ImageCardController, lineNumber=29, parameters=[ParameterInfo(name=shareCode, type=java.lang.String)], returnType=im.toss.util.api.Response)]"
    cause:  "java.lang.IndexOutOfBoundsException: toIndex (4) is greater than size (0).
    	at im.toss.teens.invitation.adapter.cache.redis.UserShareKeyEncrypter.decrypt(UserShareKeyEncrypter.kt:35)
    	at im.toss.teens.api.controller.imagecard.web.ImageCardController.getImageCard(ImageCardController.kt:29)
    	at im.toss.teens.api.controller.imagecard.web.ImageCardController$$SpringCGLIB$$0.getImageCard(<generated>
    
    

## 코드 작성하기

LLM으로 분석 요청을 보내는 코드는 다음과 같습니다.
    
    
    data class AnalyzeErrorRequest(
        val path: String,
        val httpMethod: String,
        val exception: Exception,
        val userId: Long?,
        val notify: Boolean,
        val logId: String?,
    )
    
    
    data class AnalyzeErrorResponse(
        val json: AnalyzeErrorResult,
        val success: Boolean,
        val question: String,
        val chatId: String,
        val chatMessageId: String,
        val isStreamValid: Boolean,
        val sessionId: String,
    )
    
    data class AnalyzeErrorResult(
        val action: String,
        val reason: String,
        val guide: String,
        val inference: String,
    )
    
    
    @Component
    class LlmErrorAnalyzer(
        @Qualifier("llmWebClient")
        private val llmWebClient: WebClient,
        private val llmProperties: LlmProperties
    ) : ErrorAnalyzer {
    
        fun analyze(
            request: AnalyzeErrorRequest
        ): AnalyzeErrorResponse {
            val filteredStackTrace = filterStackTrace(request.exception)
    
            return llmWebClient.call<AnalyzeErrorResponse>(
                method = HttpMethod.POST,
                uri = "/api/v1/prediction/${llmProperties.id}",
                requestBody = mapOf(
                    "question" to """
                          company: toss,
                          service: ${appId},
                          httpMethod: ${request.httpMethod.lowercase()},
                          requestUrl: ${request.path},
                          cause: ${getStackTraceAsString(request.exception.message!!, filteredStackTrace)},
                          methodSignatures:${getMethodSignatures(filteredStackTrace)}
    	                """.trimIndent()
                ),
                headersConsumer = { it.setBearerAuth(llmProperties.key) }
            )
        }
    
        fun filterStackTrace(exception: Exception): List<StackTraceElement> {
            return exception.stackTrace.filter { isTossTeamRequest(it) }
        }
    
        private fun isTossTeamRequest(it: StackTraceElement): Boolean {
            return it.className.contains("toss") && it.className.contains(llmProperties.serviceName)
        }
    
        private fun getStackTraceAsString(message: String, stackTrace: List<StackTraceElement>): String {
            return buildString {
                appendLine(message)
                stackTrace.forEach { appendLine(it) }
            }
        }
    
        fun getMethodSignatures(stackTraceElements: List<StackTraceElement>): List<MethodSignatureInfo> {
            return stackTraceElements.mapNotNull { getMethodSignature(it.className, it.lineNumber) }
        }
    
        private fun getMethodSignature(className: String, lineToFind: Int): MethodSignatureInfo? {
            val classInputStream = this.javaClass.classLoader
                .getResourceAsStream(className.replace('.', '/') + ".class")
                ?: return null
    
            val classNode = ClassNode()
            val classReader = ClassReader(classInputStream)
            classReader.accept(classNode, 0)
    
            for (method in classNode.methods) {
                val lineNumbers = mutableListOf<Int>()
    
                for (insn in method.instructions) {
                    if (insn isLineNumberNode) {
                        lineNumbers.add(insn.line)
                    }
                }
    
                if (lineToFind in lineNumbers) {
                    return extractMethodSignature(className, lineToFind, method)
                }
            }
            return null
        }
    
    
        fun extractMethodSignature(
            className: String,
            lineNumber: Int,
            method: MethodNode
        ): MethodSignatureInfo {
            val argumentTypes = Type.getArgumentTypes(method.desc)
    
            val parameterNames = method.localVariables
                .asSequence()
                .drop(1) // 첫 번째는 this (인스턴스 메서드인 경우)
                .take(argumentTypes.size)
                .map { it.name }
                .toList()
    
            val parameters = argumentTypes.mapIndexed { index, type ->
                ParameterInfo(parameterNames[index], type.className)
            }
    
            return MethodSignatureInfo(
                className = className,
                lineNumber = lineNumber,
                parameters = parameters,
                returnType = Type.getReturnType(method.desc).className
            )
        }
    
        data class MethodSignatureInfo(
            val className: String,
            val lineNumber: Int,
            val parameters: List<ParameterInfo>,
            val returnType: String,
        )
    
        data class ParameterInfo(val name: String?, val type: String)
    }

가장 먼저 발생한 Exception 객체를 바탕으로, LLM이 분석하기에 용이한 애플리케이션 정보들만을 필터링합니다. 현재는 회사명과 서비스 이름이 모두 포함된 클래스 이름을 갖는 StackTraceElement 객체만 거르고 있어요.

그 다음으로 Exception 객체가 갖는 예외 메시지와 필터링된 스택 트레이스를 문자열로 변환한 것을 문자열로 조합하여 cause 필드를 제공해주고 있습니다. 이를 통해 에러가 발생한 원인을 추적하기에 용이해져요.

그 다음으로 cause를 분석하는데 용이한 Method Signature를 제공해주고 있는데, 각각의 스택 트레이스에서 활용된 클래스 이름, 라인 번호, 파라미터 목록 그리고 반환 타입을 제공함으로써 LLM이 추론 시에 보다 정확한 컨텍스트를 갖도록 했습니다. 이를 위해서는 바이트 코드를 추출하는 코드가 작성됐어요.

그 외에도 분석 요청을 위해 path가 활용되고 있는데, 이는 HttpServetRequest가 받은 path와 가장 패턴이 매칭되는 컨트롤러의 경로를 가져온 것입니다.
    
    
    request.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE)

위와 같은 에러 분석 결과를 바탕으로 다음과 같이 메신저 알림을 보냄으로써, 팀원들 간에 비동기적 협력 가능성을 높이고 서로의 컨텍스트에 집중할 수 있는 상황을 만들 수 있었어요.

운영하면서 에러 알림 발송 기준과 발송 주기 등에 대한 정책들을 함께 논의함으로써, 최대한 효율적으로 정보들을 제공할 수 있도록 하는 작업들이 추가되었습니다.

  * 알림은 알림 요청 헤더가 존재할 경우에만 발송한다.
  * 동일한 에러의 경우 10분을 주기로 하여 발송한다.
  * 타 서버에 의한 모호한 에러가 발생 시 빠르게 확인이 가능하도록, 로그 링크를 하단에 첨부한다.
  * 기타 등등

이러한 부분을 코드로 확인하면 다음과 같아요.
    
    
    @Component
    @Profile("alpha")
    class LlmErrorReporter(
        private val llmErrorAnalyzer: ErrorAnalyzer,
        private val slackBotService: SlackOpsBotAdaptor,
        private val redisTemplate: RedisTemplate<String, Boolean>,
    ) {
    
        @Async
        fun report(request: AnalyzeErrorRequest) {
            if (!request.notify) {
                log.info { "분석 요청 헤더가 없습니다." }
                return
            }
    
            val key = createCacheKey(request)
    
            val lockSuccess = redisTemplate.opsForValue().setIfAbsent(key, true, NOTIFY_DURATION) ?: false
            if (!lockSuccess) {
                log.info { "최근 10분 이내에 발송된 요청입니다." }
                return
            }
    
            try {
                val response = llmErrorAnalyzer.analyze(request)
                if (!response.success) {
                    log.error { "처리에 실패했습니다. response=${response}" }
                    return
                }
    
                notify(request, response, key)
            } catch (e: Exception) {
                log.error(e) { "에러 분석 및 발송 중에 에러가 발생했습니다." }
            }
        }
    
        private fun createCacheKey(
            request: AnalyzeErrorRequest,
        ): String {
            return "${request.userId}:${request.path}-${request.httpMethod}-${request.exception.message}"
        }
    
        fun notify(request: AnalyzeErrorRequest, response: AnalyzeErrorResponse, key: String) {
            val result = slackBotService.sendMessageToChannel(
                "channelId",
                """
                ${response.json.action}
                ```
                action: ${response.json.action}
                request: ${request.httpMethod}${request.path}
                reason: ${response.json.reason}
                solve: ${response.json.guide}
                ```
                """.trimIndent()
            )
    
            if (result.isOk && result.ts != null) {
                slackBotService.sendMessageToThread(
                    token = "bot token",
                    channel = result.channel,
                    threadTs = result.ts,
                    text = """
                        ```
                        <https://kibana.toss.com/app/discover#/?_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:now-1d,to:now))&_a=(columns:!(path,param,response.body),filters:!(),index:aada19a0-8192-11ef-83df-0b776a10d34e,interval:auto,query:(language:kuery,query:'service%20:%20%22teens%22%20AND%20logId%20:%20%22${request.logId}%22'),sort:!(!('@timestamp',desc)))|API 호출 로그>
                        <https://kibana.toss.com/app/discover#/?_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:now-1d,to:now))&_a=(columns:!(message),filters:!(),index:a4abea90-8192-11ef-83df-0b776a10d34e,interval:auto,query:(language:kuery,query:'service%20:%20%22teens%22%20AND%20logId%20:%20%22${request.logId}%22'),sort:!(!('@timestamp',desc)))|서버 에러 로그>
                        ```
                    """.trimIndent(),
                )
            }
            redisTemplate.opsForValue().set(key, true, NOTIFY_DURATION)
        }
    
        companion object {
            val NOTIFY_DURATION = Duration.ofMinutes(10)!!
        }
    }

### 마무리

LLM은 이제 실제 업무 시에 깊게 관여하고 있고, 다방면에서 충분한 생산성을 제공할 수 있을만큼 발전했죠. 작은 불편함들을 빠르게 개선하면 팀의 생산성을 높이고, 빠른 실행력을 확보할 수 있을 것입니다. 팀원들의 따봉은 덤이고요\!

실제 위의 기능을 적용 및 운영하다보니 더 많은 정보를 제공해주어 더 많은 분석을 이끌어낼 수 있었습니다. 예를 들어 `MethodArgumentTypeMismatchException` 에러가 발생한 경우를 위해 다음과 같은 추가적인 메시지를 프롬프트로 전달하곤 했어요.
    
    
    val detailMssage = e.message + " on property ${e.propertyName}"

이러한 부분을 추가적으로 전달하여, 기존의 “정수 타입의 파라미터로 문자열이 전달되었기 때문입니다.” 와 같이 다소 불친절하던 메시지를 다음과 같이 고도화 할 수 있었습니다.

이번 에러 분석 자동화 케이스를 통해 LLM으로 앞으로 얼마나 더 업무 생산성을 높일 수 있을지 많은 기대가 생겼습니다. 앞으로도 운영을 하면서 더 많은 정보를 추가하고 예시 프롬프트를 추가하면서 상황에 맞게 점진적으로 개선해 나갈 수 있도록 하고자 합니다.