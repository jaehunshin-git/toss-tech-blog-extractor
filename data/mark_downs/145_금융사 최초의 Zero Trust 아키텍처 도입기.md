# 금융사 최초의 Zero Trust 아키텍처 도입기

**Date:** 2023년 9월 1일
**URL:** https://toss.tech/article/slash23-security

---

전통적인 환경의 보안 아키텍처는 방화벽과 같은 경계를 기준으로 신뢰와 비신뢰를 나누어서 운영이 되고 있었는데요. 신뢰 구간에서의 추가적인 보안 통제가 없으면서 신뢰의 크기가 커진다면 그만큼 보안의 Risk들도 증가하게 된다는 한계점들이 있었고, 다원화 된 Identity 관리, 보안 솔루션 관리, 재택근무 환경과 오피스 환경의 이원화된 환경을 관리함으로써 보안 가시성 확보 및 관리의 어려움, 팀원들의 업무의 불편함들을 해결하기 위해 토스에서는 제로트러스트 보안 아키텍처를 도입하게 되었는데요. 어떤 과정으로 도입하였고, 어떻게 운영 중인지 살펴보려고 합니다. 

## Zero Trust란?

고정된 네트워크 경계를 방어하는 것에서 사용자, 자산, 자원 중심의 방어로 변경하는 발전적인 사이버 보안 패러다임입니다.

제로 트러스트는 물리적 위치, 네트워크 위치, 자산 소유권을 기준으로 자산 또는 사용자 계정에 부여된 암묵적인 신뢰는 없다고 가정합니다.

## Zero Trust를 도입하기 위한 고민

Zero Trust 보안 아키텍처를 도입하기 위해서는 현재 우리가 가지고 있는 리스크들을 정리하고, 대체 혹은 보완하는 것에 대한 고민들이 필요한데요. 저희는 아래와 같은 고민을 하였습니다. 

  * Identity: 다원화된 인증 시스템 사용으로 인하여 계정, 권한 관리의 어려움으로 인해 보안 가시성이 낮아지는 부분을 통합으로 관리하여 보안 가시성을 확보
  * Device: Active Directory, PMS\(Patch Management System\) MacOS의 OS 보안 패치, SW 관리, PC 보안 정책 확보의 어려움으로 인한 대체 수단 마련
  * Network: 재택근무 시 네트워크 보안 통제의 어려움, SSL Inspection을 통한 네트워크 분석의 어려움들을 해결하는 대체 수단 마련을 통한 보안 가시성 확보및 사내 네트워크 접근 시 추가적인 보안 검증을 통한 위협 예방 
  * 각 영역에서 통제를 다른 영역과 연계하는 통제 수단 마련 

    * 예시 1\) Application 혹은 사내 네트워크 접근 시 Endpoint 정보를 식별하여, 접근 유무 결정
    * 예시 2\) 사내 네트워크에 대한 접근 통제 시 Identity 정보를 통한 접근 통제 

  * 각 영역의 이벤트들을 통합 분석하여 보안 위협 식별 및 대응 

## Zero Trust 아키텍처 주요 컴포넌트

Identity, Device, Network, Data, Application 각 영역에서의 보안성, 가시성을 확보하고, 각 영역 간 연계를 통한 추가적인 접근 통제 및 통합 보안 이벤트 분석을 통한 위협 식별 및 대응

## 주요 기능

### IAM \(Identity Access Management\) 

  * Single Sign On : Application 로그인 통합\(SAML, OIDC\)
  * RBAC\(Role Based Access Control\) : 인사 DB와 연계하여 직군, 팀 단위의 접근 제어
  * ABAC\(Attribute Based Access Control\) : Role\(권한\)이 할당 되어있더라도, 회사에서 정의한, Network, 자산, 보안을 검증을 통한 접근제어
  * Policy : Application에 접근할 때의 Factor\(ID/PW, MFA 등\) 정의, RBAC, ABAC 기반의 접근제어
  * Security : Threat Intelligence 분석 / SIEM\(Security Information Event Management\) 연동을 통한 계정 탈취와 같은 보안 위협 예방 및 방지

### SASE\(Secure Access Service Edge\)

  * Policy : SSL Inspection을 통한 암호환 된 Traffic 복호화 및 HTTPS Packet 분석 URL Filter, Application Control을 통한 유해사이트, 비인가사이트 차단
  * Data Protection :

    * DLP\(Data Loss Protection\)을 통한 회사의 중요 데이터\(내부자료, 개인정보\) 유출 모니터링, 방지
    * File Type Control: File 확장자 기반의 Upload / Download Contents 식별 및 차단
    * CASB\(Cloud Access Security Broker\)를 통한 Cloud에 보관된 중요 데이터 유출 방지

  * Threat Management : 

    * Malware: 악성코드, 랜섬웨어, 스파이웨어 등을 식별 및 차단
    * ATP\(Advanced Threat Protection\): 네트워크 트래픽 검사를 통한 악성코드, 스팽, 피싱과 같은 위협 식별 및 차단
    * Sandbox: 파일, URL, IP 등의 데이터를 분석하여 위협 식별과 악성코드 분석 및 격리

### ZTNA\(Zero Trust Network Access\)

  * Role : IAM 연동을 통한 회사 인사 DB를 활용한 내부 네트워크에 접근할 수 있는 사용자, 그룹 정의
  * Segments : 내부 네트워크에 있는 자산을 Application 단위로 정의\(Domain, IP, Port 등
  * Policy : Role, Segments를 사용한 접근제어, Role이 있는 사용자라도 EPP\(Endpoint Protection Platform\)와 연계하여 접근할 때마다 Device 보안성 검증UEM\(Unified Endpoint Management\)

### UEM\(Unified Endpoint Management\) 

  * Device Management : Device 보안, 데이터 보호, SW 등 식별 및 관리
  * Asset Management : 하드웨어, 네트워크, 사용자 정보 수집, Device 분실 시 잠금 및 초기화
  * Application Management : OS, 필수 S/W\(브라우저, 메신저, 보안 프로그램, 인증서 등\)을 자동 설치 및 패치 관리
  * Policy : Device 보안 정책 준수\(화면보호기, Disk 암호화 등\)

### EPP\(Endpoint Protection Platform\)

  * Anti-Malware : 악성코드, 랜섬웨어, 스파이웨어 등의 위협으로부터 보호
  * EDR\(Endpoint Detection & Response\) : 실시간 악성코드,공격 탐지 및 대응 Device 행동\(File System, Registry 변경, Process 실행 등\) 분석을 통한 보안 위협 탐지 및 대응 탐지된 보안 위협 정보 분석을 통한 유사한 위협 예방 및 대응
  * Device Compliance : Device에 대한 OS 보안 설정과 EPP의 보안 상태 평가, 분석, 취약점 및 위협 식별 IAM, SASE & ZTNA와 연계를 통한 접근제어

##  전환 절차 

### IAM 온보딩

관리자가 사전에 팀원들에 정보를 받아서 IAM 계정을 생성을 하고, 팀원들은 Password 설정 & MFA \(Multi Factor Authentication\)를 설정합니다.

### Active Directory 제거 & UEM Join

더 이상 Active Directory와 PMS를 통해 Device의 보안 설정과 SW 패치 관리를 하지 않을거라 Device에 스크립트를 실행시켜서 AD Join을 풀고, UEM에 IAM을 통해 로그인을 합니다. 로그인을 완료 하면, 자동으로 미리 설정해둔 Device의 보안 설정\(예시: 화면보호기 설정, 디스크 암호화 등\)을 적용하고, 더이상 사용하지 않는 Application 들은 삭제하고, 앞으로 사용해야하는 Application\(웹브라우저, 메신저, EPP, SASE, ZTNA\)는 자동으로 설치 됩니다. 

### SASE & ZTNA Login 

마지막으로 SASE & ZTNA Agent에 IAM 계정을 통해 로그인을 하면, Zero Trust 환경으로 전환 과정은 완료 됩니다. SASE와 ZTNA는 기존에 사용하던 방화벽 정책을 기반으로 Migration은 하지만, IP 기반 접근제어가 아닌, RBAC\(Role Based Access Control\) 기반 즉, 토스의 조직 정보를 기반으로 정책을 Migration 하였습니다. 

## 도입 후

### Login

저희가 사용중인 Application들을 IAM과 SSO 연동을 통해서 Application에 로그인 할 때에는 IAM 통에 인증을 완료 후 접근합니다. IAM 연동을 하기 전에는 ID/Password + OTP를 통해서만 검증을 했었다면, 이제는 신뢰된 Network 인지, 회사 자산인지, Device의 보안 수준은 준수되는지를 검증을 추가로 하여 접근을 합니다. 이 과정은 생체 인증으로 인증을 하는 과정에서 검증이 됩니다. 단, 검증하는 과정이 생겨도 로그인 속도가 지연되지 않습니다.

### Network

SaaS Application이나 인터넷을 접근할 때에는 SASE가, On-Premise나 Public Cloud와 같은 Private 네트워크에 접근할 때에는 ZTNA가 동작을 하게 되는데요. 회사에서 근무를 할 때와 재택근무를 할 때 위치에 큰 제약 없이 회사에 있을 때와 동일한 보안 환경으로 업무용 시스템 어디든 접속이 가능합니다. 단, 업무용 시스템에 접속 할 때 접속하는 Device가 보안을 준수하고 있는지 빠르게 검증하고, 인터넷을 할 때는 피싱 사이트와 같은 곳으로부터 안전하게 회사의 자산과 데이터를 보호합니다.

### RBAC & ABAC 

인사DB와 IAM을 연동하고, IAM과 Application, Network 등을 연동하여 팀원의 직무\(Role\)을 기반의 접근제어를 통한 접근제어 정책을 구성하여 보안정책의 가시성을 확보하고, 팀원의 퇴직 시에는 자동으로 할당된 권한이 회수되고, 직무의 변경이 있을 때 자동으로 권한이 회수되고, 변경된 직무에 맞는 권한으로 재 할당이 됩니다.

## 마치며

토스에서 Zero Trust 아키텍처 도입을 통해 보안 가시성 확보, 보안 관리의 효율화를 하면서도 팀원들의 업무 편의성도 향상되었습니다. 

글을 마무리하면서, 글의 내용을 요약하자면 아래와 같습니다. 

  * Zero Trust란 고정된 네트워크 경계를 방어하는 것에서 사용자, 자산, 자원 중심의 방어로 변경하는 발전적인 사이버 보안 패러다임입니다. 
  * IAM, ZTNA, UEM, EPP, SIEM등을 연계하여 상호 보완적으로 Zero Trust 아키텍처를 구축하였습니다.
  * Zero Trust 아키텍처를 도입 후 각 영역에서 보안 가시성 확보, 보안 관리의 효율화를 진행하면서도 팀원들의 업무 편의성도 향상되었습니다.

DLP\(Data Loss Protection\)을 통한 회사의 중요 데이터\(내부자료, 개인정보\) 유출 모니터링, 방지 File Type Control: File 확장자 기반의 Upload / Download Contents 식별 및 차단 CASB\(Cloud Access Security Broker\)를 통한 Cloud에 보관된 중요 데이터 유출 방지