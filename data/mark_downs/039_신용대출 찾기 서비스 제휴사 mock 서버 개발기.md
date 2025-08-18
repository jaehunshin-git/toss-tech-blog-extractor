# 신용대출 찾기 서비스 제휴사 mock 서버 개발기

**Date:** 2025년 6월 13일
**URL:** https://toss.tech/article/credit-loan-partner-mock-server

---

안녕하세요, 토스 신용대출 찾기 서비스 팀 Server Developer 류경린입니다.

신용대출 찾기 서비스는 다양한 제휴사의 대출 상품을 연동하여, 고객이 보다 편리하게 대출 상품을 탐색하고 신청할 수 있도록 돕는 서비스입니다. 

이번 글에서는 신규 제휴사 연동 이후 제휴사의 테스트 서버가 유효한 응답을 주지 않거나, 특정 케이스를 테스트하기 어려운 상황을 어떻게 해결했는지, 그리고 이를 위해 설계한 mock 서버를 소개하고자 해요.

## 배경

신규 제휴사 연동 이후 다음과 같은 문제들이 반복적으로 발생했어요.

  * 제휴사 개발 서버의 불안정한 응답 혹은 장애
  * 특정 퍼널 또는 고객 조건에 맞는 테스트 데이터 확보의 어려움
  * 테스트 과정에서 실제 제휴사 서버로부터 유효한 응답을 받기 어려운 상황

이러한 문제들은 QA 및 신규 기능 개발 효율을 떨어뜨릴 뿐 아니라, 서비스 출시 일정에도 영향을 주었습니다. 이를 해결하기 위해 사용자, 제휴사, 퍼널 단위로 정밀하게 동작을 제어할 수 있는 mock 서버를 설계했어요.

## 용어 정리

본격적인 설명에 앞서, 대출 도메인과 관련된 주요 용어를 간략히 정리할게요.

  * 제휴사: 은행, 저축은행, 보험사 등 대출 상품을 제공하는 금융기관
  * 가심사 조회: 고객 정보를 활용해 대출 금리, 한도 등을 간단히 확인하는 행위
  * 대출 신청: 가심사 결과를 바탕으로 고객이 특정 상품에 대해 대출을 신청하는 행위
  * 대출 실행: 제휴사가 고객 정보를 활용해 대출을 실행하고 자금을 입금하는 행위

## 요구사항

기능적 / 비기능적 요구사항은 아래와 같았어요.

### 기능적 요구사항

  * 유저, 제휴사, 퍼널 단위로 mock 사용 여부를 설정할 수 있어야 한다.
  * 동기/비동기 응답 방식을 모두 지원해야 한다.
  * relay 서버 역할을 수행해야 한다.
  * 유저가 쉽게 설정할 수 있어야 한다.

### 비기능적 요구사항

  * 기존 비즈니스 로직은 변경하지 않는다.
  * mock 서버에서 로직을 처리하기 위해 필요한 값은 커스텀 헤더로 전달한다.
  * 토스 내 타 서비스에서도 mock 서버를 손쉽게 연동할 수 있는 유연한 구조를 제공한다.

## 설계 및 구현

mock 서버는 다음과 같은 구성요소로 설계되었습니다.

  * 커스텀 헤더 주입
  * 설정
  * 예약\(비동기 응답 지원\)
  * mock 데이터 생성
  * Relay 서버 역할
  * 메신저봇 연동
  * 유연한 연동 구조 제공

### 1\. 커스텀 헤더 주입

신용대출 찾기 서비스는 mock 동작 여부나 mock 데이터 생성 시 필요한 유저 정보를 클라이언트 요청의 헤더를 통해 주입받습니다. 이렇게 하면 비즈니스 로직에는 전혀 영향을 주지 않고, 테스트를 유연하게 제어할 수 있어요.

> 테스트 환경에서만 동작하도록 @Profile\("dev"\) 설정을 통해 관리하며, 실제 통신 로직\(RestTemplate, WebClient\)에서 헤더 주입이 이뤄집니다.

RestTemplate

  * RestTemplate에는 인터셉터를 통해 요청마다 헤더를 추가할 수 있어요. 아래는 유저 ID와 원장 ID를 주입하는 예시입니다.
  * 해당 인터셉터를 `RestTemplate`에 등록하면, 모든 제휴사 요청에 자동으로 헤더가 포함됩니다.
        
        class MockServerHeaderInjectionInterceptor : ClientHttpRequestInterceptor {
            override fun intercept(
                request: HttpRequest,
                body: ByteArray,
                execution: ClientHttpRequestExecution,
            ): ClientHttpResponse {
                val headers = request.headers
                headers.add(MOCK_SERVER_HEADER_X_REQUEST_ID, "ids")
                headers.add(MOCK_SERVER_HEADER_X_USER_ID, "userId")
        
                return execution.execute(request, body)
            }
        }

WebClient

  * WebClient에서는 `ExchangeFilterFunction`을 활용해 헤더를 주입해요. 아래는 동일한 목적의 필터 예시입니다.
  * WebClient 설정 시 이 필터를 `.filter(addMockServerHeaderFilter())`와 같이 등록해주면 돼요.
        
        private fun addMockServerHeaderFilter(): ExchangeFilterFunction {
            return ExchangeFilterFunction.ofRequestProcessor { clientRequest: ClientRequest ->
                val injectedHeaders = ClientRequest.from(clientRequest)
                    .headers { headers: org.springframework.http.HttpHeaders ->
                        headers.add(MOCK_SERVER_HEADER_X_REQUEST_ID, "ids")
                        headers.add(MOCK_SERVER_HEADER_X_USER_ID, "userId")
                    }
                    .build()
                Mono.just(injectedHeaders)
            }
        }

### 2\. 설정

모든 설정값은 DB 테이블에서 관리하여 유연성을 확보했어요.

  * `partner_metadata`: 제휴사 메타데이터

    * 응답의 동기 / 비동기 방식 여부
    * 네트워크 설정
    * 암호화 여부 등

  * `partner_response`: 퍼널별 mock 응답 데이터

    * mock 데이터
    * 응답 결과 json layout 등

  * `user_status`: 유저별 mock 응답 사용 여부 및 응답 지연 설정

    * 콜백 을 N 초 후에 받을 것인지
    * 특정 퍼널 에 대해 어떤 mock 응답을 받을 것인지 등

정의된 정보를 사용해 mock 응답 을 생성합니다.
    
    
    val key = Triple(companyId, funnelType, status)
    // 주어진 정보를 사용해 response 를 생성한다.
    val response = partnerResponseService.create(key, metadata, requests)

### 3\. 예약

mock 서버에서는 실제 제휴사처럼 콜백 응답을 지연하여 전송하는 기능이 필요합니다. 이를 통해 비동기 응답을 테스트할 수 있도록 지원하며, 실제 서비스 환경을 더 현실감 있게 시뮬레이션할 수 있어요.

예약은 다음과 같이 두 단계로 구성됩니다.

1\. 예약 등록

  * 가심사 조회나 대출 신청 API 호출 시점에, 예약 정보를 DB에 저장합니다.
  * 각 요청에 대해 몇 초 후 콜백을 호출할 지 결정되며, 이 설정은 유저 설정\(`user_status`\) 또는 제휴사 메타데이터\(`partner_metadata`\)에 정의된 값을 사용합니다.
  * 저장된 예약 정보는 `schedule.executeTs` 필드에 실행 시점을 기록합니다.

2\. 예약 실행

  * mock 서버에서는 `@Scheduled`를 사용해 1분 단위로 주기적인 예약 조회 작업을 수행합니다.
  * 실행 시점\(`executeTs`\)이 지난 예약 건들을 조회한 후, `ThreadPoolTaskScheduler`를 사용해 콜백 API 요청을 실제로 전송합니다.

    
    
    private fun reserveInternal(schedule: ScheduleEntity, forceReserve: Boolean = false) {
      handlers
          .filter { it.canHandle(schedule) }
          .forEach { handler ->
              repository.save(schedule)
              if (forceReserve) {
                  schedule.reserve()
                  repository.save(schedule)
                  scheduler.schedule(
                      { submitTask(schedule, handler) },
                      schedule.executeTs.atZone(ZoneId.systemDefault()).toInstant(),
                  )
                  return@forEach
              }
    
              lockExecutor.runOnce(
                  lockKey = "$LOCK_KEY_PREFIX${schedule.id}",
                  lockDuration = Duration.ofMinutes(1),
              ) {
                  schedule.reserve()
                  repository.save(schedule)
                  scheduler.schedule(
                      { submitTask(schedule, handler) },
                      schedule.executeTs.atZone(ZoneId.systemDefault()).toInstant(),
                  )
              }
          }
      }

### 4\. mock 데이터 생성

mock 응답은 실제 제휴사 응답과 동일한 포맷으로 생성되어야 해요. 특히 상품명, 금리, 한도, 기간 등의 값은 토스 원장 데이터와 정합성 있게 주입되어야 하며, 이를 위해 다음과 같은 흐름으로 데이터를 생성합니다.

1\. 예약어 기반 mock 템플릿 정의

  * 각 제휴사별 응답 포맷에 따라 mock 템플릿을 사전에 정의합니다.
  * 이 템플릿은 `"{{amount}}"`, `"{{productId}}"`와 같은 예약어를 포함해요.

    
    
    {
      "amount": "{{amount}}",
      "period": "{{period}}",
      "interestRate": "{{interestRate}}",
      "productId": "{{productId}}",
      "id": "{{id}}"
    }
    
    

2\. 예약어 치환

  * 응답 JSON 내의 예약어를 실제 원장 데이터로 치환합니다.
  * 이 때 `JsonNode` 객체를 순회하며 깊은 중첩 구조까지 치환되도록 설계했어요.

    
    
    fun replace(
        replaceParams: Map<String, String>,
        node: JsonNode,
    ): JsonNode {
        when {
            node.isObject -> {
                val objectNode = node as ObjectNode
                objectNode.fields().forEach { (key, value) ->
                    replaceParams.forEach { (keyword, replaceKeyword) ->
                        if (value.asText() == keyword) {
                            objectNode.put(key, replaceKeyword)
                        }
                    }
                    replace(replaceParams, value)
                }
            }
            node.isArray -> {
                val arrayNode = node as ArrayNode
                arrayNode.forEach { replace(replaceParams, it) }
            }
            node is Collection<*> -> {
                node.filterIsInstance<JsonNode>()
                    .forEach { replace(replaceParams, it) }
            }
        }
        return node
    }

  * 예를 들어, `"{{productId}}"`는 실제 상품명으로 `"{{amount}}` 는 대출 한도로 치환됩니다.

    
    
    {
      "amount": "10000000",
      "period": "12",
      "interestRate": "2.4",
      "productId": "OOO 자동차 담보 대출",
      "id": "{{id}}"
    }

3\. 상품명 → 원장 아이디 매핑 처리

  * 각 원장에 매핑된 고유한 `productId`를 기반으로 다시 한 번 ID 매핑을 수행합니다.
  * `loan_product_id_property_names` 필드를 통해 각 제휴사마다 어떤 필드명이 상품명인지를 메타데이터로 관리하고 있기 때문에, 이를 기준으로 정확한 치환이 가능해요.

    
    
    private fun replace(
        propertyNames: List<String>,
        keyword: String,
        replaceKeywordByPropertyNames: Map<String, String>,
        node: JsonNode,
    ) {
        when {
            node.isObject -> {
                val objectNode = node as ObjectNode
                val propertyName = propertyNames.firstNotNullOfOrNull { objectNode.get(it)?.asText() }
    
                // objectNode.fields.value 가 ObjectNode 일 수 있기 때문에 반드시 objectNode 의 전체 field 를 순회한다.
                objectNode.fields().forEach { (key, value) ->
                    if (value.asText() == keyword) {
                        // keyword 를 templateValue 로 치환한다.
                        val templateValue = replaceKeywordByPropertyNames[propertyName]!!
                        objectNode.put(key, templateValue)
                    }
                    replace(propertyNames, keyword, replaceKeywordByPropertyNames, value)
                }
            }
            node is Collection<*> -> {
                node.filterIsInstance<JsonNode>()
                    .forEach { replace(propertyNames, keyword, replaceKeywordByPropertyNames, it) }
            }
            node.isArray -> {
                val arrayNode = node as ArrayNode
                arrayNode.forEach { replace(propertyNames, keyword, replaceKeywordByPropertyNames, it) }
            }
        }
        return
    }

  * 예를 들어, “OOO 자동차 담보 대출” 상품명 에 맞는 거래번호 123456789가 치환됩니다.

    
    
    {
      "amount": "10000000",
      "period": "12",
      "interestRate": "2.4",
      "productId": "OOO 자동차 담보 대출",
      "id": "123456789"
    }

### 5\. Relay 서버

mock 서버 는 아래 2가지 상황에 대해 relay 서버 역할을 해야 해요.

  * 유저가 mock 응답 을 사용하지 않는 경우
  * 제휴사 에서 콜백 API 를 호출하는 경우

유저가 mock 응답을 사용하지 않는 경우, 아래처럼 직접 제휴사 를 호출해 응답을 relay 합니다.
    
    
    if (userStatus?.getPartnerResponseStatus(type) != null) {
      return getMockResponse()
    }
    val response = callPartner()

제휴사에서 콜백 API 를 호출하는 경우

제휴사에서 토스로 콜백 API 를 호출 하는 경우, api gateway를 통해 해당 요청이 인입돼요.

api gateway의 routing rule 을 신용대출 찾기 서버 에서 mock 서버로 수정해, mock 서버에서 콜백 API를 받고 이를 다시 신용대출 찾기 서버로 호출합니다.

### 6\. 메신저봇 을 활용한 mock 설정

팀내에서 사용하고 있는 메신저봇에 mock 서버 설정 및 설정을 확인할 수 있는 기능을 추가합니다.

현재 제휴사, 퍼널 별 mock 설정 확인 버튼을 클릭해 현재 어떤 제휴사의 어떤 퍼널 에 대해 mock 데이터를 사용하고 있는지를 쉽게 알 수 있어요.

제휴사, 퍼널 mock 설정 버튼을 클릭해 특정 제휴사 의 어떤 퍼널에 대해 mock 데이터를 사용할지 쉽게 설정할 수 있습니다.

### 7\. 유연한 연동 구조 제공

mock 서버는 토스 내 다양한 제휴사 연동 서비스들이 손쉽게 통합 및 활용할 수 있도록 확장 가능하고 유연한 아키텍처를 제공해요. 제휴사 연동 서비스는 검색, 신청, 취소, 상태 조회의 크게 네 가지 기능을 수행합니다.

모듈 구조

mock 서버는 모듈화된 구조를 통해 서비스별로 손쉽게 연동할 수 있도록 설계되었어요. 각 서비스에서 mock 서버를 연동할 경우, 해당 서비스 전용 모듈만 추가하면 되는 구조입니다.

  * `mock-server-api` : 각 서비스로부터 요청을 수신하는 API 모듈
  * `mock-server-base` : 콜백, 치환 기능 등 모든 서비스에서 공통적으로 사용할 수 있는 기능 및 추상화된 Handler를 제공하는 기반 모듈
  * `mock-server-serviceA` : 특정 서비스의 비즈니스 로직을 담은 모듈
  * `mock-server-serviceA-admin` : 특정 서비스의 어드민 기능을 포함한 모듈

Multi DataSource 지원

서비스 모듈마다 별도의 데이터 소스\(DataSource\)를 사용해야 하는 경우가 있어, Spring 기반에서 Multi DataSource를 구성할 수 있는 세 가지 방식 중 아래와 같은 특징을 고려해 Class 기반 정의 방식을 채택했어.

  * base package 기준 정의
  * annotation 기반 정의
  * class 기반 정의 ✅

채택 사유:

1\. Repository 상속 구조에 불편함

  * `admin` 모듈은 어드민 특화 쿼리를 별도로 정의합니다.
  * 동시에 기존 서비스 모듈의 공통 Repository 기능도 재사용해야 합니다.
  * 따라서 `admin` 모듈의 repository 클래스는 서비스 모듈의 repository를 상속하는 구조입니다.

2\. 어노테이션 중복 선언 문제

  * 어노테이션 기반\(@ServiceARepository\) 으로 설정할 경우, 서비스 모듈의 repository 클래스와 어드민 모듈의 repository 클래스 양쪽에 동일한 어노테이션을 선언해야 하는 번거로움이 발생합니다.
  * 이는 유지보수 시 의도치 않은 설정 누락 혹은 중복을 유발할 수 있고, 설정 관리가 복잡해집니다.

3\. 패키지 구조의 자율성 확보

  * 모듈 단위로 동일한 패키지 구조를 사용할 수 있기 때문에 base package 스캔 방식 역시 적용이 어렵습니다.

프로퍼티 설정 전략

각 모듈에서 필요한 설정은 모듈 내부의 `application-{service}.properties` 파일을 통해 정의해요.

기존에는 `mock-server-base`의 `application.properties`에 모든 설정을 통합할 수도 있었지만, 각 설정이 어떤 서비스에 영향을 미치는지를 명확히 구분하고 관리하기 어려운 점을 고려하여 모듈별로 분리하는 방식을 선택했어요.

최종적으로는 base 모듈의 `application.properties`에서 `spring-cloud-config` 및 각 서비스의 설정 파일\(`application-{service}.properties`\)을 import하여, 모든 프로퍼티를 통합적으로 로딩할 수 있도록 구성합니다.

## 마치며

대외 기관과의 연동을 다루는 많은 회사들이 저희와 유사한 어려움을 겪고 있을 거라 생각해요.

토스의 신용대출 찾기 서비스 팀은 mock 서버와 relay 기능을 결합한 테스트 환경을 누구나 쉽게 이용할 수 있게 구축함으로써, 테스트 효율성과 신뢰성을 모두 확보할 수 있었습니다.

이 글이 유사한 문제를 고민하고 있는 개발자분들께 실질적인 도움이 되었으면 좋겠습니다. 감사합니다.