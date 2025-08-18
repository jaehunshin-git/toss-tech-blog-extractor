# Kotlin으로 DSL 만들기: 반복적이고 지루한 REST Docs 벗어나기

**Date:** 2022년 4월 11일
**URL:** https://toss.tech/article/kotlin-dsl-restdocs

---

REST Docs 테스트 코드량을 70% 줄여주는 DSL 개발기

읽는 데 걸리는 시간: 6분

## DSL

Domain Specific Languages\(DSL\)은 코드의 내부 로직을 숨기고 재사용성을 올려줍니다. 어떤 경우는 비 개발자가 사용하도록 고안되는 경우도 있어서, 일반적인 프로그래밍 언어보다 훨씬 쉬운 사용성을 가집니다. 핵심은 해당 도메인을 아는 사람이면 누구나 쉽게 해당 도메인을 제어할 수 있도록 DSL을 제공하는것이 목적이며, 그렇기 때문에 프로그래밍 언어가 아닌 일반적인 언어에 가깝도록 호출 방식을 설계합니다. 때문에 DSL 호출 내부에서 어떤 로직이 작동하는지는 사용자가 알도록 할 필요가 없으며 훨씬 더 간결하고 빠르게 코드를 작성할 수 있습니다.

### Spring REST Docs, 더 쉽고 간결하게 쓸 수 없을까

토스페이먼츠에서는 API docs를 REST Docs를 사용해서 작성할 수 있도록 권장하고 있습니다. docs를 작성하는 행위 자체에서부터 API를 통합테스트할 수 있다는 점이 매력적이며, 인터페이스의 의도치 않은 변경을 감지할 수 있다는 장점이 있습니다. 문제는 독스를 작성할 때마다 테스트 코드를 작성해줘야 하기 때문에 Swagger 보다 더 번거롭게 작업하게 된다는 문제가 있습니다.

이 글에서는 DSL을 통해서 API 인터페이스의 안정성과 개발자의 생산성을 모두 가져갈 수 있는 방법을 소개합니다.

## REST Docs DSL

먼저 기존의 작성법\(AS-IS\)과 DSL을 이용한 작성법\(TO-BE\)을 비교해보겠습니다.

### AS-IS.

### TO-BE.

한 눈에 봐도 간결해보이지 않나요? AS-IS에서 볼 수 있듯, 기존의 작성법은 여러 문제가 있습니다.

  1. 반복적인 코드 호출이 많음.기존 작성법으로 작성할 때마다 생산성 저하를 느꼈습니다. API를 만드는 시간만큼이나 docs를 생성하는 시간이 걸린다니, 이것 참 비효율이지 않나요?
  2. 코드가 장황하여 읽히지 않음.인터페이스에 변화가 생기면 REST Docs 테스트 코드를 수정해야 하는데, 어떤 코드를 수정해야 하는지 빠르게 찾기가 어려웠습니다. 즉 해당 코드가 무엇을 수행하는지 한번에 읽기가 힘들고, 이 코드 수행 결과가 어떤 docs를 만들어낼지 단번에 떠올리기 어렵다는 단점이 있었습니다.

첫 번째 단점은 기존의 다른 코드로부터 복붙으로 시간을 좀 줄여낼 수는 있었지만, 두 번째 단점은 참 신경 쓰였습니다. 저는 JSON과 같은 간결한 구조로부터 docs를 테스트하는 코드가 만들어지길 원했습니다.

## Kotlin으로 DSL 만들기

다행히도 Kotlin은 여러 함수 선언 방식이 존재하여서, 이런 문제를 풀기에 매우 좋습니다. Kotlin의 테스트 코드 라이브러리인 Kotest와 MockK이 대표적인 사례라고 생각합니다.

### infix 함수

[Infix Notation \(kotlinlang.org\)](https://kotlinlang.org/docs/functions.html#infix-notation)

잘 만들어진 DSL은 인간의 자연어를 사용하듯이 자연스럽게 쓰고 읽힐 수 있어야 한다고 생각합니다. Kotlin의 infix notation은 이 목표를 달성하기에 최적의 도구입니다.

`"data.businessId" type NUMBER`는 `"data.businessId".type(NUMBER)`와 동일한 효과를 낳습니다.
    
    
    infix fun String.type(                    // (1)
        docsFieldType: DocsFieldType
    ): Field {                                // (2)
        ...                                   // (3)
    }

  * \(1\):

    * infix notation으로 해당 함수를 선언해줍니다.
    * type이라는 함수는 String을 receiver로 받는 함수입니다.
    * 파라미터는 docsFieldType 하나만 받습니다 \(`DocsFieldType`는 아래에서 서술합니다.\)

  * \(2\): 원래 restdocs가 제공하던 FieldDescriptor를 유연하게 다루기 위해 Field라는 Wrapper 클래스를 정의합니다.
  * \(3\): 원래의 RestDocs를 만들던 동작을 수행합니다

infix 함수를 사용할때는 제한사항이 있습니다.

  * 호출할때는 receiver와 parameter가 명시적으로 있어야 함 \(this로 암시적인 전달 불가능\)
  * parameter는 하나여야 함 \(default value도 지정할 수 없음\)

그래야만 "data" type OBJECT 처럼 간결한 구조를 만들어 낼 수 있기 때문입니다.

### DocsFieldType

REST Docs에서는 응답, 요청 필드의 type을 JsonFieldType으로서 구분합니다.

여기에 저는 자주 사용하는 format인 Date, DateTime을 쉽게 정의할 방법을 찾고 싶었고, enum class도 간단히 전달하여 어떤 필드가 사용될 수 있는지 docs에 쉽게 표기하고 싶었습니다. date, datetime, enum은 모두 JsonFieldType.STRING이지만 format과 sample이 다르게 표시될 필요가 있는 특이 케이스이기 때문입니다.

이런 식으로 정의한다면 아래 예시와 같이 간단하게 `Field`를 생성해내면서 `DocsFieldType`을 정의해낼 수 있습니다.
    
    
    "data" type OBJECT
    "id" type NUMBER
    "createdAt" type DATETIME

### DocsFieldType - enum

다만 enum을 정의하고 싶을때는 조금 디테일이 필요합니다.
    
    
    "companyType" type STRING example CompanyType::class

로도 선언할 수는 있지만 매번 example을 호출해주는 건 조금 귀찮습니다. 어차피 enum이 string이라는건 누구나 다 아는 사실인데 두 함수 호출을 나눠야 할까요?
    
    
    "companyType" type ENUM(CompanyType::class)

훨씬 간결해졌습니다.

다음과 같이 DocsFieldType을 확장한 sealedSubclass를 만든다면 위와 같은 dsl 작성이 가능합니다.
    
    
    data class ENUM<T : Enum<T>>(val enums: Collection<T>) : DocsFieldType(JsonFieldType.STRING) {
      constructor(clazz: KClass<T>) : this(clazz.java.enumConstants.asList())   // (1)
    }

  * \(1\): secondary constructor 덕분에 모든 enum값이 아니라 특정 조건에 맞는 enum 값을 collection으로 넘길수도 있습니다.

    * ex\) 개인사업자에 해당하는 companyType만 해당 필드에 존재할 수 있을 때 `"individualCompanyType" type ENUM(CompanyType.values().filter { it.isIndividual() })`

이로써 type infix 함수는 아래와 같이 완성할 수 있습니다.
    
    
    infix fun String.type(docsFieldType: DocsFieldType): Field {
        val field = createField(this, docsFieldType.type)
        when (docsFieldType) {
            is DATE -> field formattedAs RestDocsUtils.DATE_FORMAT
            is DATETIME -> field formattedAs RestDocsUtils.DATETIME_FORMAT
            else -> {}
        }
        return field
    }
    
    infix fun <T : Enum<T>> String.type(enumFieldType: ENUM<T>): Field {
        val field = createField(this, JsonFieldType.STRING, false)
        field.format = EnumFormattingUtils.enumFormat(enumFieldType.enums)
        return field
    }
    
    private fun createField(value: String, type: JsonFieldType, optional: Boolean): Field {
        val descriptor = PayloadDocumentation.fieldWithPath(value)
            .type(type)
            .attributes(RestDocsUtils.emptySample(), RestDocsUtils.emptyFormat(), RestDocsUtils.emptyDefaultValue())
            .description("")
    
        if (optional) descriptor.optional()
    
        return Field(descriptor)
    }
    
    

### Field 클래스에서 DSL 확장하기

이제 좀 더 욕심을 내봅시다. 위 예시처럼 얼마든지 함수 호출을 chaining할 수 있습니다.

어떤가요? 괄호로 계속 호출하는 것보다 좀 더 직관적이지 않나요?

type이라는 infix function이 `Field`를 반환할 수 있도록 했으니, `Field`에서 더 많은 DSL을 호출하도록 확장할 수 있게 되었습니다.
    
    
    open class Field(
        val descriptor: FieldDescriptor,
    ) {
        val isIgnored: Boolean = descriptor.isIgnored
        val isOptional: Boolean = descriptor.isOptional
    
        protected open var default: String
            get() = descriptor.attributes.getOrDefault(RestDocsAttributeKeys.KEY_DEFAULT_VALUE, "") as String
            set(value) {
                descriptor.attributes(RestDocsUtils.defaultValue(value))
            }
    
        protected open var format: String
            get() = descriptor.attributes.getOrDefault(RestDocsAttributeKeys.KEY_FORMAT, "") as String
            set(value) {
                descriptor.attributes(RestDocsUtils.customFormat(value))
            }
    
        protected open var sample: String
            get() = descriptor.attributes.getOrDefault(RestDocsAttributeKeys.KEY_SAMPLE, "") as String
            set(value) {
                descriptor.attributes(RestDocsUtils.customSample(value))
            }
    
      	open infix fun means(value: String): Field {
            return description(value)
        }
    
        open infix fun attributes(block: Field.() -> Unit): Field {
            block()
            return this
        }
    
        open infix fun withDefaultValue(value: String): Field {
            this.default = value
            return this
        }
    
        open infix fun formattedAs(value: String): Field {
            this.format = value
            return this
        }
    
        open infix fun example(value: String): Field {
            this.sample = value
            return this
        }
    
        open infix fun isOptional(value: Boolean): Field {
            if (value) descriptor.optional()
            return this
        }
    
        open infix fun isIgnored(value: Boolean): Field {
            if (value) descriptor.ignored()
            return this
        }
    }
    
    

이렇게 얼마든지 코드를 확장해나갈 수 있을뿐더러, 해당 프로젝트에서 사용하는 REST Docs snippet의 attribute를 코드 상으로 좀 더 명확하게 정의할 수 있게 되었습니다.

## 마무리

이 글은 REST Docs의 반복적인 코드를 제거하고, docs의 생성이라는 본래의 목적을 달성하고자 기존 MockMvc 테스트코드 작성법에서 벗어나, REST Docs DSL을 만드는 방식으로 문제를 해결하고자 했습니다.

우리가 흔히 쓰는 gradle configuration 작성 방식인 build.gradle.kts 또한 org.gradle.kotlin.dsl에서 그 선언 방식을 찾아볼 수 있고, MockK이나 Kotest에서도 다양한 방식으로 Kotlin의 장점을 최대한 끌어낸 모습을 확인할 수 있습니다.

  * build.gradle.kts \(<https://github.com/gradle/kotlin-dsl-samples>\)
  * MockK의 every\(<https://mockk.io/#dsl-examples>\),
  * Kotest의 여러 Testing Styles\(<https://kotest.io/docs/framework/testing-styles.html>\)

혹시나 여러분도 반복적인 작업을 일일히 복붙으로 하고 있다면 여러분의 팀만을 위한 DSL을 만들어보는 건 어떨까요?

이 REST Docs DSL은 토스페이먼츠 *엔지니어링 데이에 장태영\(Server Developer, taeyoung.jang@tosspayments.com\)님과 함께 만들었습니다.

  * 토스페이먼츠에서는 매주 목요일에 엔지니어링 데이를 진행하고 있어요. 이 시간에는 평소 업무에 병목이 되는 문제들을 해결하거나, 인프라를 개선하는 등의 작업을 진행합니다.