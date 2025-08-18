# @use-funnel 개발기 #2: 기존 라이브러리를 어떻게 뜯어 고칠 것인가?

**Date:** 2024년 12월 13일
**URL:** https://toss.tech/article/use-funnel-2

---

안녕하세요. 토스 Frontend Developer 강민우입니다.

토스팀 프론트엔드 챕터는 이전부터 퍼널에 관해 [SLASH23 발표](https://toss.im/slash-23/session-detail/A1-3)도 했었고, Slash Library에 `[use-funnel](https://www.slash.page/ko/libraries/react/use-funnel/README.i18n)`를 오픈소스로 배포하는 등 퍼널 라이브러리를 꾸준히 대내외적으로 사용하고 있었습니다. 그런데 기존에 사용하던 퍼널 라이브러리에는 다음과 같은 문제점들이 발견되기 시작했어요. 문제의식에 대한 더 자세한 내용은 이전의 [선영님의 아티클](https://toss.tech/article/use-funnel-1)을 읽어보세요.

  * Next.js에 의존성이 있기 때문에, `react-router-dom`을 사용하는 곳에서 쓰기 어려웠어요. 혹은 라우터를 사용하지 않는 곳에서 퍼널 상태를 관리하고 싶은 니즈도 있었고요.

기존 @toss/use-funnel 패키지는 next를 의존성으로 요구한다.

  * 각각의 단계별로 상태 관리를 지원하지 않기 때문에 이전 단계에서 입력한 상태를 현재 단계에서 있다는 것을 따로 증명해야 됐어요.
  * 뒤로가기를 했을 때 현재 페이지에 있던 상태를 사용하고 싶지 않았어요. 기존 라이브러리에서는 상태를 히스토리에 연동하지 않기 때문입니다.
  * 다양한 추가 기능을 넣고 싶은데 그러한 인터페이스가 마련되어 있지 않았어요. 예를 들어, 약관동의를 BottomSheet로 띄운 컴포넌트를 하나의 단계로 사용하기 어려웠어요.

이런 문제로 사내에서 워킹그룹으로 새롭게 `[@use-funnel](https://use-funnel.slash.page/ko)` 오픈소스 라이브러리를 개발하기 시작했어요. 이전 아티클에서는 문제의식과 워킹그룹의 타임라인을 공유드렸다면 이번 아티클에서는 라이브러리의 구현에 대해서 더 자세히 살펴볼게요.

## Next.js 의존성 제거

먼저 Next.js 뿐만 아니라 다른 라우터를 지원하기 위해서 모노레포 형태의 콘셉트을 잡았습니다. `@use-funnel/core` 라는 패키지를 통해 핵심 기능을 만들어 둔 후, `createUseFunnel` 이라는 훅을 만드는 함수를 패키지에서 반환하도록 했습니다.
    
    
    // @use-funnel/core
    export function createUseFunnel(useRouter) {
    	return function useFunnel(options) {
    		const router = useRouter(options);
    		// ... 퍼널 관련 코드들
    	}
    }

그리고 라우터를 구현하는 `@use-funnel/next` , `@use-funnel/react-router-dom` 패키지에서 실제 퍼널 상태를 만드는데 필요한 것들을 구현하도록 했습니다.
    
    
    import { createUseFunnel } from '@use-funnel/core';
    import { useMemo, useState } from 'react';
    
    export const useFunnel = createUseFunnel(({ id, initialState }) => {
      const [history, setHistory] = useState([initialState]);
      const [currentIndex, setCurrentIndex] = useState(0);
      return useMemo(
        () => ({
          history,
          currentIndex,
          currentState: history[currentIndex],
          push(state) {
            setHistory((prev) => [...prev.slice(0, currentIndex + 1), state]);
            setCurrentIndex((prev) => prev + 1);
          },
          replace(state) {
            setHistory((prev) => {
              const newHistory = prev.slice(0, currentIndex + 1);
              newHistory[currentIndex] = state;
              return newHistory;
            });
          },
          go: (index) => setCurrentIndex((prev) => prev + index),
        }),
        [history, currentIndex],
      );
    });

이를 통해 `react-router-dom`, `@react-navigation/native` 등 다양한 라우터 등을 대응할 수 있게 되었고, 커스텀한 상태를 구현할 경우를 위한 케이스를 위해 직접 `@use-funnel/core` 패키지를 가져와서 구현할 수 있게 되었습니다.

## 단계별로 상태 관리 안전하게 할 수 있게 하기

이렇게 만들어지는 `useFunnel()` 훅에 단계로 별로 상태 관리를 어떻게 정의할까요? 
    
    
    // 기존의 useFunnel()
    const [Funnel, setFunnel] = useFunnel(['AStep', 'BStep', 'CStep'] as const);
    
    // 새로운 useFunnel()
    const funnel = useFunnel<{
      AStep: { foo?: string;bar?: string };
      BStep: { foo: string; bar?: string };
      CStep: { foo: string; bar: string };
    }>({
      initial: {
        step: 'AStep',
        context: {}
      }
    });

기존에는 단순히 단계 배열을 요구하는 것이었지만, 새로운 `useFunnel()`을 사용할 때 각각의 단계별로 상태를 타입스크립트 제네릭으로 정의할 수 있게 했습니다. 
    
    
    // 기존 렌더링
    <Funnel>
      <Funnel.Step name="AStep"><AStep /></Funnel.Step>
      <Funnel.Step name="BStep"><BStep /></Funnel.Step>
      <Funnel.Step name="CStep"><CStep /></Funnel.Step>
    </Funnel>
    
    // 새로운 방식
    switch (funnel.step) {
      case 'AStep': return <AStep />;
      case 'BStep': return <BStep foo={funnel.context.foo} />;
      case 'CStep': return <CStep foo={funnel.context.foo} bar={funnel.context.bar} />;
    }

또한, 단계별로 상태를 추론하기 위해서 기존의 컴포넌트만 반환해주던 결과에서 구별된 유니온\(Discriminated unions\)을 반환해서 각 단계와 상태를 타입 안전하게 사용할 수 있도록 했어요.
    
    
    switch (funnel.step) {
      case 'AStep': {
    	  return (
    		  <AStep
    			  // BStep으로 이동하기 위해서는 `foo` 가 반드시 필요!
    			  onNext={foo => funnel.history.push('BStep', { foo })}
    		  />
    	  );
      }
      case 'BStep': {
    	  return (
    		  <BStep
    			  foo={funnel.context.foo}
    			  onNext={bar => funnel.history.push('CStep', { bar })}
    			  // AStep으로 이동하기 위해서는 아무런 조건이 없어도 되므로 상태를 안 넘겨줘도 됨.
    			  onReplace={() => funnel.history.replace('AStep')}
    		  />
    	  );
      }
      case 'CStep': return <CStep foo={funnel.context.foo} bar={funnel.context.bar} />;
    }

그리고 안전하게 다음 단계로 넘어가기 위해서, 단계를 변경할 때 해당 단계에 필요한 상태가 있는지 비교해서 꼭 필요한 상태가 누락되면 타입 오류가 나도록 했습니다.

예를 들어, 위 예제에서 “AStep” 의 경우 “BStep” 으로 이동하기 위해서 `foo` 프로퍼티가 필수로 요구되며, “BStep” 에서 “AStep” 으로 이동하기 위해서는 필수로 요구하지 않습니다.

이를 구현하기 위해서 타입스크립트에서 현재 단계의 상태 타입과 이동 단계의 상태 타입을 비교해서 달라진 상태가 있는지 확인했어요. 상태가 다르면 단계 이동 함수에서 반드시 상태를 기입하도록 했어요.
    
    
    type CurrentStep = { foo: string; bar?: string };
    type TargetStep = { foo: string; bar: string };
    
    // { foo?: string; bar: string }
    // CurrentStep에서 이미 foo가 존재하기 때문에 foo를 optional하게 요구합니다.
    type Input = CompareMergeContext<CurrentStep, TargetStep>;

`CompareMergeContext` 타입의 자세한 구현체가 궁금하시면 이걸 열어주세요\! 

또한 런타임 밸리데이션을 통해 상태 검증을 구현해야 하는 경우, 제네릭 선언 없이 단계를 정의해서 사용할 수 있도록 했습니다.
    
    
    import { z } from 'zod';
    
    const AStepZod = z.object({ foo: z.string().optional(), bar: z.string().optional() });
    const BStepZod = AStepZod.required({ foo: true });
    const CStepZod = BStepZod.required({ bar: true });
    
    const funnel = useFunnel({
      steps: {
        AStep: { parse: AStepZod.parse },
        BStep: { parse: BStepZod.parse },
        CStep: { parse: CStepZod.parse },
      },
      initial: {
        step: 'AStep',
        context: {},
      }
    });

## 다양한 추가 기능을 구현하기 위한 인터페이스

토스에서는 유저에게 이용약관 및 개인정보 처리 동의를 받기 위해 같은 바텀시트를 활용한 UI를 자주 사용하는데요, 이러한 UI를 하나의 단계로 표현하고 싶은 니즈가 있었습니다.

기존의 `useFunnel()` 에서는 별도로 이전의 단계의 상태를 저장하고 있지 않기 때문에 이러한 구현이 조금 어려웠습니다.

새로운 버전의 `useFunnel()`에서는 이러한 다양한 문제를 해결하기 이전 단계들의 상태를 저장하고, 이를 쉽게 사용하기 위해 훅에서 반환되는 Render 컴포넌트를 만들었습니다.
    
    
    const funnel = useFunnel(...);
    
    <funnel.Render
    	AStep={({ history }) => (
    		<AStep
    		  // BStep으로 이동하기 위해서는 `foo` 가 반드시 필요!
    		  onNext={foo => history.push('BStep', { foo })}
    	  />
      )}
      BStep={({ context, history }) => (
    	  <BStep
    		  foo={context.foo}
    		  onNext={bar => history.push('CStep', { bar })}
    		  // AStep으로 이동하기 위해서는 아무런 조건이 없어도 되므로 상태를 안 넘겨줘도 됨.
    		  onReplace={() => history.replace('AStep')}
    	  />
      )}
      CStep={({ context }) => <CStep foo={context.foo} bar={context.bar} />}
    />

이 컴포넌트 따로 switch-case 없이 모든 단계의 렌더링을 쉽게 사용할 수 있는 용도로도 사용할 수 있습니다.

여기에서 `AStep`에서 `BStep`으로 이동할 때, `AStep`의 렌더링을 그대로 유지한 채 `BStep`의 렌더링을 보여주고 싶었습니다. 이를 위해 `funnel.Render.overlay` 라는 구현체로 렌더 함수를 감싸서, 내부에서 처리하도록 했습니다.
    
    
    <funnel.Render
    	AStep={({ history }) => (
    		<AStep
    		  // BStep으로 이동하기 위해서는 `foo` 가 반드시 필요!
    		  onNext={foo => history.push('BStep', { foo })}
    	  />
      )}
      BStep={funnel.Render.overlay(({ context, history }) => (
    	  <BStep
    		  foo={context.foo}
    		  onNext={bar => history.push('CStep', { bar })}
    		  // AStep으로 이동하기 위해서는 아무런 조건이 없어도 되므로 상태를 안 넘겨줘도 됨.
    		  onReplace={() => history.replace('AStep')}
    	  />
    	)}
      CStep={({ context }) => (
    	  <CStep foo={context.foo} bar={context.bar} />
      )}
    />

내부 구현은 간단하게 다음과 같습니다.
    
    
    const renderEntires: Array<{ step: string; element: React.ReactNode }> = [];
    
    // Overlay를 렌더링할 때, renderBeforeOverlay에 먼저 렌더링할 단계의 컴포넌트들을 배열(renderEntires)에 추가합니다.
    if (render.type === 'overlay') {
      declare const renderBeforeOverlay: Array<{ step: string; element: React.ReactNode }>;
      renderEntries.push(...renderBeforeOverlay);
    }
    
    renderEntires.push(render(funnelRenderStep));
    
    return (
      <Fragment>
        {renderEntires.map((entry) => (
          <Fragment key={entry.step}>{entry.element}</Fragment>
        ))}
      </Fragment>
    );

Render 컴포넌트는 항상 배열을 통해 현재 퍼널 단계를 렌더링하고 있습니다. 현재 퍼널 단계가 Overlay이라면 이전 단계를 배열에 담아서 렌더링을 하도록 했습니다.

추가로 Render 컴포넌트를 통해 한 가지 편의 기능을 추가한 것이 있습니다. 바로 현재 단계에서 조건에 따라 여러 단계의 퍼널로 갈 때 사용하기 좋은 `funnel.Render.with` 입니다.
    
    
    <funnel.Render
    	AStep={funnel.Render.with({
    	  events: {
    	    GoBStepWithFoo(foo: string, { history }) {
    	      history.push('BStep', { foo })
    	    },
    	    GoBStepWithBar(bar: number, { history }) {
    	      history.push('BStep', { bar })
    	    },
    	    GoCStep(_, { history }) {
    	      history.push('CStep')
    	    }
    	  },
    	  render({ dispatch }) {
    		  return (
    			  <AStep
    			    onFoo={foo => dispatch('GoBStepWithFoo', foo)}
    			    onBar={bar => dispatch('GoBStepWithBar', bar)}
    			    onC={() => dispatch('GoCStep')}
    			  />
    		  );
    	  }
    	})}
    />

복잡한 퍼널에서 이동 규칙과 렌더링 규칙을 나눠줌으로써 응집성 있는 퍼널을 기대할 수 있게되었습니다.

## 마치며

토스에서는 이러한 공통된 관심사를 가진 사람들을 모아 워킹그룹을 운영할 수 있어요. 저에게는 이것이 첫 워킹그룹이었는데요, 단순히 사내 라이브러리 개선에서 시작해 오픈소스까지 발전해서 업무와 병행하느라 힘들었지만 그만큼 보람이 매우 깊었습니다. 

앞으로도 많은 기능과 개선을 꾸준히 진행할 예정입니다. `@use-funnel` 많이 사용해주시고 문제 있으면 언제든지 이슈를 남겨주세요. 

토스 프론트엔드 챕터는 [@use-funnel](https://use-funnel.slash.page/ko) 외에도 여러 오픈소스를 운영하고 있습니다. 토스에서 운영중인 오픈소스는 [여기](https://github.com/toss)서 확인하실 수 있어요.