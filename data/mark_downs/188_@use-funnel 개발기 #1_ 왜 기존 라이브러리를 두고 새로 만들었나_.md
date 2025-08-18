# @use-funnel 개발기 #1: 왜 기존 라이브러리를 두고 새로 만들었나?

**Date:** 2024년 12월 9일
**URL:** https://toss.tech/article/use-funnel-1

---

안녕하세요. 토스 Frontend Developer 권선영입니다.

오늘은 토스에서 강력하고 안전한 단계별 상태 관리 라이브러리 `@use-funnel`을 어떻게 만들게 되었는지 소개드릴게요. 제 경험이 사내에서 문제의식을 공유하고 해결 방법을 찾으려는 분들께 도움이 되면 좋겠어요.

## 처음 맞이한 퍼널 문제

때는 작년, 제가 팀을 이동하면서 주택담보대출 비교하기 서비스\(이하 주담대 서비스\)를 맡게 됐습니다. 이전까진 저는 데스크탑 환경에서 사용하는 사내 어드민을 만들었는데요. 주담대 서비스는 모바일 앱 안에서 웹뷰 서비스를 만들다보니 이전과는 고려할 부분들이 꽤 달랐습니다. 그중에서도 가장 큰 차이점은 아주 복잡한 퍼널을 개발해야 한다는 점이었어요.

그 당시 주담대 서비스는 2가지 방식으로 퍼널을 관리하고 있었습니다. 사내에서 널리 사용하고 있던 `[use-funnel](https://www.slash.page/ko/libraries/react/use-funnel/README.i18n)`\(오늘 소개할 `@use-funnel`과 이름이 유사하지만 서로 다른 라이브러리입니다\)을 활용하는 방식과 서비스의 전임자가 새롭게 시도했던 [XState](https://xstate.js.org/)를 사용한 방식이에요.

`use-funnel`을 이용한 방식은 익숙하고, 직관적인 코드로 읽기 쉬운 장점이 있었지만, 제대로 된 상태관리를 지원하지 않아 상태관리는 퍼널과 별개로 직접 해야 하는 문제가 있었어요.
    
    
    interface FormState {
      purpose: Purpose;
      address: string;
      income: number;
    }
    
    function Funnel() {
      const [formState, setFormState] = useState<Partial<FormState>>({});
      const [Funnel, setStep] = useFunnel([FunnelName.대출목적선택, FunnelName.담보물선택, FunnelName.연소득입력], {
        initialStep: FunnelName.대출목적선택,
        stepQueryKey: 'mortgage-loan-funnel',
      });
    
      return (
        <Funnel>
          <Funnel.Step name={FunnelName.대출목적선택}>
            <대출목적선택
              onNext={purpose => 
                setFormState(prev => ({ ...prev, purpose }));
              }}
            />
          </Funnel.Step>
          <Funnel.Step name={FunnelName.담보물선택}>
            <담보물선택
              onNext={(address) => {
                setFormState(prev => ({ ...prev, address }));
              }}
            />   
          </Funnel.Step>
          <Funnel.Step name={FunnelName.연소득입력}>
            <연소득입력
              onNext={(income) => {
                setFormState(prev => ({ ...prev, income }));
              }}
            />   
          </Funnel.Step>
        </Funnel>
      );
    };

`XState`를 사용한 방식은 퍼널의 단계와 상태를 함께 관리할 수 있는 장점이 있었지만, 퍼널 컴포넌트와 상태관리 코드가 분리되어 있어 한눈에 파악하기 어려운 문제가 있었어요. 

또한, 당시 서비스 코드에서는 좀 더 안전한 코드 작성하기 위해 `XState`의 타입 대부분이 재정의 되어있었습니다. 이는 퍼널의 각 단계별로 상태 타입을 더 안전하게 관리할 수 있게 해줬지만, 선언해야 하는 타입이 너무 많아지는 문제도 있었어요.

게다가 에러 메시지가 친절하지 않아 에러가 발생한 지점을 알기 어려웠어요. 퍼널에서 입력받는 값을 하나 추가하려면 타입 정의, XState의 Machine 정의, 퍼널 컴포넌트, 이렇게 3 군데를 모두 수정해야 됐어요. 그중 한 군데를 먼저 건드리면 바로 에러가 표시되고 모든 곳에 코드를 적절하게 고쳐야 에러가 사라졌는데, IDE에 표시되는 에러 메시지가 불친절하다 보니 처음 서비스를 수정하는 사람에게는 꽤 큰 진입장벽이었습니다.
    
    
    interface Context {
      purpose: Purpose;
      address: string;
      income: number;
    }
    
    type Event = 
    | { type: "대출목적선택완료"; payload: { purpose: Purpose }}
    | { type: "담보물선택완료"; payload: { address: string }}
    | { type: "연소득입력완료"; payload: { income: number }};
    
    type StateType = 
    | { value: "대출목적선택"; event: "대출목적선택완료"; context: Partial<Context> }
    | { value: "담보물선택"; event: "담보물선택완료"; context: Partial<Context> & Pick<Context, "purpose"> }
    | { value: "연소득입력"; event: "연소득입력완료"; context: Partial<Context> & Pick<Context, "purpose" | "address"> }
    | { value: "입력완료"; context: Context };
    
    function createFunnelMachine() {
      return (
        createMachine<Partial<Context>, Event, StateType>({
    		  id: "mortgage-loan-funnel",
    		  initial: "대출목적선택",
    		  states: {
    				대출목적선택: {
    					entry: [assign(context => 대출목적선택State검증(context))],
    					on: {
    						대출목적선택완료: [
    						  {
    						    target: "담보물선택",
    						    actions: [assign()],
    						  }
    						]
    					}
    				},
    				담보물선택: {
    					entry: [assign(context => 담보물선택State검증(context))],
    					on: {
    						담보물선택완료: [
    						  {
    						    target: "연소득입력",
    						    actions: [assign()],
    						  }
    						]
    					}
    				},
    				연소득입력: {
    					entry: [assign(context => 연소득입력State검증(context))],
    					on: {
    						연소득입력완료: [
    						  {
    						    target: "입력완료",
    						    actions: [assign()],
    						  }
    						]
    					}
    				},
    				입력완료: {
    				  entry: [assign(context => 입력완료State검증(context))],
    				}
    		  }
        })
      );
    }
    
    function Funnel() {
      const [funnelMachine] = useState(() => createFunnelMachine());
      // useMachineRouter는 dispatch 시점에 적절한 다음 퍼널로 라우트시켜주는 기능을 구현한 hook이에요
      // 내부적으로 XState의 useMachine을 사용해요
      const [render, state] = useMachineRouter(funnelMachine);
    
      return (
        <>
          {render({
            대출목적선택: ({ dispatch }) => (
              <대출목적선택
    	          onNext={purpose => 
    	            dispatch({ type: "대출목적선택완료", payload: { purpose }})
    	          }}
    	        />
            ),
            담보물선택: ({ dispatch }) => (
              <담보물선택
    	          onNext={address => 
    	            dispatch({ type: "담보물선택완료", payload: { address }})
    	          }}
    	        />
            ),
            연소득입력: ({ dispatch }) => (
              <연소득입력
    	          onNext={income => 
    	            dispatch({ type: "연소득입력완료", payload: { income }})
    	          }}
    	        />
            ),
            입력완료: ({ context }) => (
              <입력완료 context={context} />
            )
          })}
        </>
      );
    }

공통적으로 둘 다 퍼널에서의 뒤로가기와 앞으로가기에 따른 적절한 상태 업데이트 관리가 쉽지 않았어요.

뒤로가기 시 이상적인 상태

당시의 뒤로가기 시 상태

위와 같은 퍼널이 존재할때 A → B → C → B\(뒤로가기\) 했다고 가정합니다. 이때 이상적인 상태는 처음 B에 진입했을 때의 상태만 가지는 것이겠지만, 따로 처리해주지 않는 한 상태는 이전에 B에서 선택한 값을 그대로 유지한 채 뒤로가기 됩니다. 이는 일자로 쭉 이어지는 퍼널에서는 큰 문제가 되지 않습니다. 

하지만 아래와 같은 퍼널이라면 어떨까요?

A → B → C → B\(뒤로가기\) → A\(뒤로가기\) → D → E로 이동한다고 했을때 선택한적 없어야하는 B의 값을 D, E 퍼널에서 가지고 있게 됩니다. 이 상태를 그대로 서버에 넘긴다거나 하면 문제가 생길 수 있겠죠.

그렇다면 제가 개발하던 주담대 서비스의 퍼널은 어떻게 생겼을까요?

## 퍼널 상태를 잘 관리하기 위한 여정

위에 보이는 이미지는 주택담보대출 서비스 디자인 시안의 일부입니다. 보이는 바와 같이 아주 복잡한 퍼널을 가지고 있었기에 퍼널의 상태을 더 잘 관리하는데 많은 고민을 하게 되었습니다.

### 5월 9일: 퍼널 토론회 공지

토스에는 퍼널을 가진 서비스가 아주 많기 때문에 저만 이런 고민을 하는 게 아닐 거라고 생각했습니다. 개선을 위한 어떤 행동을 시작하기 전에 프론트엔드 개발자들의 고충을 모아보고자 사내 메신저에 아래와 같은 공지를 올렸어요.

### 5월 14일: 퍼널 토론회

위 공지를 통해 퍼널 개발 경험을 가진 12명의 FE개발자들이 모였어요. 1시간의 열정적인 논의 끝에 그동안 어떤 부분에 어려움이 있었고, 새로운 도구를 만든다면 어떤 부분을 지원하면 좋을지 정리했어요. 아래는 당시 정리했던 요구사항의 일부입니다.

  * 안정적인 뒤로가기/앞으로가기 지원
  * 모달, 바텀싯과 같은 오버레이를 하나의 스텝으로 사용하는 기능 지원
  * 외부로 노출되는 인터페이스가 잘 고려되면 좋겠다.
  * 코드를 한 곳에서 한눈에 파악할 수 있으면 좋겠다.
  * 히스토리 관리를 특정 라이브러리 의존성 없이 플러그인으로 붙일 수 있으면 좋겠다.

### 5월 22일: 워킹그룹 첫 모임

모였던 12명의 동료분들 중 지원을 받아 새로운 도구를 같이 만들 워킹그룹을 구성하고 새로운 라이브러리를 만들기 시작했어요. 당시 토스 프론트엔드 챕터에서는 사내 라이브러리를 적극적으로 오픈소스화하는 중에 있었는데요, 퍼널관리 라이브러리는 비즈니스 로직 의존성이 없기 때문에 처음부터 오픈소스로 공개하는 것을 목표로 만들기로 했어요.

워킹그룹에는 저를 포함하여 5명이 모였는데요, 5명이 다 같이 코드를 짜는 것은 비효율적이기 때문에 아래와 같은 루틴으로 진행하며 라이브러리를 만들기로 했어요.

  1. 다 같이 모여 1주 동안 작업한 분량과 그에 대한 방향성을 정한다.
  2. 1에서 논의한 내용을 바탕으로 코드 작성을 맡은 2인이 페어로 라이브러리를 코드를 작성한다.
  3. 다 같이 모여 작성된 코드에 대해 리뷰하고, 다음 주 작업 분량과 방향성을 정한다.
  4. 1-3 반복

위 과정을 통해 약 2달간 `@use-funnel/core`와 이를 사용하여 `browser router`, `next`, `react-router-dom`, `react-navigation-native`에서 사용 가능한 버전의 라이브러리를 만들었습니다.

### 7월 29월: 사내 배포 테스트 시작

`@use-funnel`은 처음부터 오픈소스를 염두에 두고 만들었기 때문에 문서화도 매우 중요한 부분이었습니다. 다른 사내 라이브러리 문서의 구조를 참고하여 뼈대를 만들고 다른 개발자분들이 참고할 수 있는 예시 코드를 잘 작성하려고 노력했어요.

[문서](https://use-funnel.slash.page/)가 준비되자마자 `next`를 사용하는 모바일 웹뷰 서비스와 `react-router-dom`을 사용하는 데스크탑 어드민 제품 개발자 2분께 새로 만든 `@use-funnel` 적용을 부탁드리고 버그 제보와 후기 및 개선 아이디어를 받았습니다. 이후 사내 공지 후 약 1달간 사내 테스트 기간을 거쳤습니다. 이 과정에서 몇 가지 버그들을 잡을 수 있었습니다.

### 8월 19일: 오픈 소스 공개

그리고 드디어 8월 19일에 `@use-funnel`을 오픈소스로 공개했어요. 오픈소스 공개 이후에 빠르게 외부 사용자로부터 피드백, PR을 받기 시작했어요. 제가 팀에서 겪었던 문제를 해결하려고 만든 라이브러리가 다양한 사용자에게 도움을 준다는 점이 뿌듯하고 신기했던 거 같아요. `@use-funnel`에 대한 자세한 기능 소개는 다음 글에 이어집니다.

토스 프론트엔드 챕터는 `@use-funnel` 외에도 여러 오픈소스를 운영하고 있습니다. 토스에서 운영 중인 오픈소스는 [여기](https://github.com/toss)서 확인하실 수 있어요.