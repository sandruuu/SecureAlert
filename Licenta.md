# Arhitectura și Implementarea unei Soluții Securizate de Acces Distant bazată pe Zero Trust Network Access și Autentificare Multifactor

## Evoluția Paradigmei de Securitate în Accesul la Distanță: De la Perimetru la Identitate

Transformarea digitală accelerată din ultimul deceniu a redefinit fundamental modul în care organizațiile își gestionează resursele informaționale. Într-un mediu globalizat, caracterizat de o mobilitate extremă a utilizatorilor și de o distribuție geografică a activelor, conceptul tradițional de securitate perimetrală - bazat pe ideea că interiorul rețelei este sigur, iar exteriorul este periculos - a devenit o relicvă tehnologică ineficientă.<sup>1</sup> Expansiunea modelelor de lucru hibrid și utilizarea infrastructurilor de tip cloud au demonstrat că firewall-ul clasic nu mai poate asigura confidențialitatea și integritatea datelor atunci când suprafața de atac s-a extins dincolo de pereții fizici ai biroului.<sup>1</sup>

Accesul securizat la distanță reprezintă astăzi un pilon central al strategiilor de securitate cibernetică, necesitând mecanisme care să contracareze atacuri sofisticate precum interceptarea traficului, mișcarea laterală și, cel mai critic, compromiterea credențialelor.<sup>1</sup> Studiile recente indică faptul că majoritatea breșelor de securitate exploatează parole slabe sau furate, ceea ce subliniază nevoia imperativă de a implementa soluții de Autentificare Multifactor (MFA) care să nu fie doar un strat adițional, ci fundamentul accesului.<sup>1</sup> Totuși, MFA tradițional, bazat pe coduri primite prin SMS sau notificări push, începe să prezinte vulnerabilități în fața atacurilor de tip „MFA fatigue" sau a proxy-urilor de phishing.<sup>5</sup> Din acest motiv, cercetarea de față propune o arhitectură bazată pe standarde moderne, precum FIDO2 și WebAuthn, integrate într-un model de tip Zero Trust Network Access (ZTNA).<sup>1</sup>

În această nouă paradigmă, încrederea nu este niciodată acordată implicit. Orice cerere de acces, indiferent dacă provine din interiorul sau exteriorul rețelei corporative, trebuie să fie verificată explicit, autorizată pe baza principiului celui mai mic privilegiu și monitorizată continuu pentru detectarea anomaliilor.<sup>3</sup> Această lucrare explorează proiecția și implementarea unei astfel de soluții, utilizând tehnologii de ultimă oră precum protocolul WireGuard pentru transportul datelor, limbajele de programare Rust și Go pentru performanță și siguranță, și mecanisme de analiză dinamică a riscului pentru a asigura o protecție adaptivă în timp real.<sup>1</sup>

## Cadrul Teoretic: Pilonii Modelului Zero Trust și NIST 800-207

Standardul NIST SP 800-207 reprezintă autoritatea definitorie pentru Arhitectura Zero Trust (ZTA), mutând focusul de la segmentele de rețea la resursele individuale.<sup>3</sup> Această schimbare este esențială deoarece, într-o rețea tradițională, odată ce un atacator trece de perimetru, acesta are adesea acces neîngrădit la întregul intranet. ZTA elimină această posibilitate prin impunerea unei segmentări logice stricte, unde fiecare conexiune este tratată ca o tranzacție discretă.<sup>11</sup>

### Componentele Logice ale Arhitecturii Zero Trust

Conform specificațiilor NIST, o implementare riguroasă a modelului Zero Trust se bazează pe separarea clară a planului de control de planul de date, orchestrată prin intermediul a trei componente majore <sup>10</sup>:

| **Componentă** | **Rol în Arhitectură** | **Funcționalitate Detaliată** |
| --- | --- | --- |
| **Policy Decision Point (PDP)** | Centrul de Decizie | Analizează datele contextuale și decide dacă accesul este permis sau respins pe baza politicilor de securitate definite.<sup>1</sup> |
| --- | --- | --- |
| **Policy Enforcement Point (PEP)** | Executorul de Politici | Un sistem responsabil pentru activarea, monitorizarea și terminarea conexiunilor între un subiect și o resursă.<sup>2</sup> |
| --- | --- | --- |
| **Policy Information Point (PIP)** | Sursa de Context | Furnizează informații externe (identitate, threat intelligence, starea dispozitivului) necesare PDP-ului pentru a lua o decizie informată.<sup>8</sup> |
| --- | --- | --- |

PDP-ul este el însuși compus din două elemente: Motorul de Politici (Policy Engine - PE) și Administratorul de Politici (Policy Administrator - PA). Motorul de Politici utilizează algoritmi de încredere pentru a evalua cererea, în timp ce Administratorul de Politici comunică decizia către PEP pentru a deschide „poarta" de acces către resursă.<sup>13</sup> Această dinamică permite sistemului să reevalueze în mod constant încrederea pe parcursul unei sesiuni, putând termina o conexiune imediat ce un parametru de risc (cum ar fi detectarea unui malware pe dispozitiv) se modifică.<sup>2</sup>

### Cele Șapte Tenete ale Zero Trust

O soluție securizată de acces distant trebuie să adere la principiile fundamentale stabilite de NIST <sup>3</sup>:

- **Toate sursele de date și serviciile de calcul sunt considerate resurse.** Nu există distincție între accesarea unui fișier local sau a unei aplicații SaaS.<sup>3</sup>
- **Toate comunicațiile sunt securizate indiferent de locația rețelei.** Securitatea nu depinde de apartenența la un segment de rețea „de încredere".<sup>3</sup>
- **Accesul la resursele individuale este acordat pe bază de sesiune.** Încrederea nu este permanentă; fiecare cerere este evaluată independent.<sup>12</sup>
- **Accesul la resurse este determinat de politici dinamice.** Acestea includ identitatea utilizatorului, starea dispozitivului și atributele comportamentale.<sup>3</sup>
- **Organizația monitorizează și măsoară integritatea tuturor activelor deținute și asociate.** Niciun dispozitiv nu are voie să se conecteze dacă nu este într-o stare de conformitate verificată.<sup>3</sup>
- **Toate autentificările și autorizările resurselor sunt dinamice și strict aplicate înainte de a permite accesul.** Aceasta este baza conceptului de „verificare explicită".<sup>3</sup>
- **Organizația colectează cât mai multe informații despre starea actuală a activelor și a infrastructurii.** Datele colectate sunt folosite pentru a îmbunătăți continuu politicile de securitate.<sup>3</sup>

## Analiza Tehnologiilor de Tunelare și Transport: Revoluția WireGuard

În centrul oricărei soluții de acces la distanță se află protocolul de tunelare. Tradițional, IPsec și OpenVPN au fost standardele industriei, însă acestea sunt criticate pentru complexitatea lor masivă, codul sursă voluminos (sute de mii de linii de cod) și performanța scăzută pe hardware-ul modern.<sup>4</sup> Această complexitate nu reprezintă doar o barieră în calea performanței, ci și un risc major de securitate, deoarece un volum mare de cod este mult mai greu de auditat pentru vulnerabilități.<sup>4</sup>

Protocolul WireGuard, lansat inițial de Jason A. Donenfeld în 2016, a apărut ca o soluție disruptivă.<sup>4</sup> Cu un design minimalist de aproximativ 4.000 de linii de cod, WireGuard urmărește să fie mai rapid, mai simplu și mai sigur decât orice predecesor.<sup>4</sup> Acesta adoptă o abordare conservatoare și modernă a criptografiei, utilizând primitive de ultimă generație care elimină riscurile asociate cu negocierea flexibilă a algoritmilor de criptare (cipher agility), o sursă comună de atacuri de tip downgrade în protocoalele mai vechi.<sup>4</sup>

### Fundamentele Criptografice ale WireGuard

WireGuard utilizează un set fix de primitive criptografice de înaltă performanță <sup>9</sup>:

| **Funcție Criptografică** | **Algoritm Utilizat** | **Avantaje** |
| --- | --- | --- |
| **Criptare Simetrică** | ChaCha20-Poly1305 | Mult mai rapid decât AES pe procesoarele care nu au instrucțiuni hardware dedicate; oferă autentificare integrată.<sup>9</sup> |
| --- | --- | --- |
| **Schimb de Chei** | Curve25519 (ECDH) | Oferă un nivel ridicat de securitate cu chei scurte și procesare rapidă.<sup>9</sup> |
| --- | --- | --- |
| **Hashing / MAC** | BLAKE2s | Mai rapid decât SHA-3 sau HMAC-SHA256, menținând o rezistență ridicată la coliziuni.<sup>9</sup> |
| --- | --- | --- |
| **Key Derivation** | HKDF | Standard industrial pentru derivarea cheilor de sesiune.<sup>17</sup> |
| --- | --- | --- |
| **Protecția Identității** | Noise Protocol Framework | Asigură confidențialitatea și Perfect Forward Secrecy (PFS).<sup>17</sup> |
| --- | --- | --- |

Un aspect inovator al WireGuard este conceptul de „Cryptokey Routing". Această tehnică asociază fiecare cheie publică cu o listă de adrese IP autorizate (AllowedIPs) în interiorul tunelului.<sup>17</sup> Atunci când serverul primește un pachet, acesta verifică dacă cheia publică a expeditorului corespunde adresei IP sursă a pachetului. Dacă nu există o corespondență, pachetul este eliminat imediat. Această legătură directă între identitatea criptografică și rutarea rețelei este un element fundamental pentru construirea unei rețele Zero Trust, deoarece previne spoofing-ul de IP la nivel de tunel.<sup>19</sup>

### WireGuard în Contextul ZTNA: BoringTun și Implementările în Rust

În timp ce implementarea originală a WireGuard în kernel-ul Linux oferă cea mai bună performanță, arhitecturile moderne de securitate, precum cele de la Cloudflare, preferă adesea implementările în spațiul utilizatorului (userspace) pentru o mai mare flexibilitate și siguranță.<sup>9</sup> BoringTun, dezvoltat de Cloudflare în limbajul Rust, este o implementare de referință care demonstrează că se poate obține o viteză comparabilă cu cea a kernel-ului fără riscurile de securitate asociate cu scrierea codului în C.<sup>9</sup>

Rust este ales pentru aceste implementări critice datorită modelului său unic de „ownership" și „borrow checking", care elimină la nivel de compilare majoritatea vulnerabilităților de memorie (cum ar fi buffer overflows sau use-after-free) care au afectat istoric serviciile de securitate.<sup>9</sup> Pentru un proiect de licență, utilizarea unei biblioteci precum defguard_wireguard_rs demonstrează o înțelegere profundă a necesității de a securiza nu doar protocolul, ci și implementarea sa software.<sup>21</sup>

## Autentificarea Modernă: De la OTP la FIDO2 și WebAuthn

Autentificarea este prima linie de apărare în orice soluție de acces distant. În fișa temei de licență, se pune un accent deosebit pe Autentificarea Multifactor (MFA) ca metodă de a reduce riscul de compromitere a conturilor.<sup>1</sup> Totuși, evoluția amenințărilor necesită o analiză critică a metodelor de MFA disponibile.

### Clasificarea Factorilor de Autentificare

MFA presupune utilizarea a cel puțin două categorii distincte de factori <sup>1</sup>:

- **Ceva ce știi (Knowledge):** Parole, PIN-uri, întrebări de securitate.
- **Ceva ce ai (Possession):** Token-uri hardware (YubiKey), aplicații de autentificare (TOTP), dispozitive mobile.<sup>1</sup>
- **Ceva ce ești (Inherence):** Biometrie (amprentă, recunoaștere facială, scanare de iris).<sup>1</sup>

În timp ce sistemele bazate pe TOTP (Time-based One-Time Password), precum Google Authenticator, sunt populare, ele nu sunt rezistente la atacurile de tip phishing în timp real, unde un atacator poate captura codul și îl poate folosi pe site-ul legitim în fereastra de validitate de 30 de secunde.<sup>5</sup>

### WebAuthn: Standardul de Aur pentru Autentificarea 

WebAuthn (Web Authentication) este o specificație W3C care permite serverelor să autentifice utilizatorii folosind criptografia cu chei publice în loc de parole.<sup>7</sup> Este componenta principală a cadrului FIDO2 și oferă trei avantaje majore <sup>23</sup>:

- **Strong:** Autentificarea este susținută hardware (Hardware Security Module), ceea ce face imposibilă extragerea cheilor private.<sup>7</sup>
- **Scoped:** O pereche de chei este validă doar pentru un anumit domeniu (origin). Un browser va refuza să folosească o cheie înregistrată pentru compania.ro pe un site clonat compania-login.ro, neutralizând complet phishing-ul.<sup>22</sup>
- **Attested:** Serverul poate verifica dacă authenticator-ul folosit (ex. un anumit model de YubiKey) este certificat și are proprietățile de securitate declarate.<sup>23</sup>

Integrarea WebAuthn într-o soluție de acces distant permite realizarea unui flux de tip „Passwordless" sau „Passkeys", unde utilizatorul se autentifică printr-un simplu gest (atingerea senzorului de amprentă sau a tastei de securitate), oferind o experiență de utilizare superioară și o securitate de neegalat.<sup>1</sup>

## Arhitectura Detaliată a Soluției Propuse

Pentru a obține o notă maximă și a demonstra o complexitate ridicată, propunem o arhitectură de tip Microservicii, containerizată prin Docker, care separă strict planul de date de cel de control.<sup>1</sup> Această abordare respectă principiile ZTNA și permite scalarea independentă a componentelor.

### Componentele Sistemului

Arhitectura este structurată pe patru module funcționale interconectate:

- **ZTNA Gateway (The PEP):** Construit pe baza unui reverse proxy de înaltă performanță (Nginx) sau a unui serviciu custom în Go/Rust. Rolul său este de a intercepta cererile de acces la resurse și de a verifica prezența unui token de sesiune valid.<sup>2</sup>
- **Identity & Risk Engine (The PDP):** Dezvoltat în Python (FastAPI) sau Go. Acesta este „creierul" sistemului, unde are loc validarea credențialelor, verificarea MFA prin WebAuthn și calcularea scorului de risc.<sup>1</sup>
- **Endpoint Agent:** Un mic serviciu care rulează pe dispozitivul utilizatorului (scris în Rust pentru acces la nivel scăzut) și colectează date despre „sănătatea" sistemului (versiune OS, prezența antivirusului, stare firewall).<sup>1</sup>
- **Resource Layer:** Aplicațiile și datele interne protejate (ex. un server de fișiere, un portal intranet), care sunt complet izolate în rețeaua privată și nu au IP-uri publice.<sup>1</sup>

### Matricea Tehnologică a Proiectului

| **Strat** | **Tehnologie Propusă** | **Justificare** |
| --- | --- | --- |
| **Backend API** | Python (FastAPI) | Asincron, rapid, suport excelent pentru biblioteci de securitate (PyOTP, WebAuthn).<sup>1</sup> |
| --- | --- | --- |
| **Data Plane / Proxy** | Nginx + OpenResty | Permite scrierea de logică de control în Lua direct la nivelul proxy-ului pentru viteză.<sup>1</sup> |
| --- | --- | --- |
| **Tunelare Securizată** | WireGuard-rs (Rust) | Oferă transport criptat cu performanță superioară și siguranța memoriei.<sup>9</sup> |
| --- | --- | --- |
| **Bază de Date** | PostgreSQL | Robustă, suportă tipuri de date complexe pentru stocarea politicilor ABAC.<sup>1</sup> |
| --- | --- | --- |
| **Cache / Sesiuni** | Redis | Latență minimă pentru verificarea token-urilor JWT și rate-limiting.<sup>1</sup> |
| --- | --- | --- |
| **MFA / FIDO2** | Library python-fido2 | Implementare certificată a serverului WebAuthn.<sup>27</sup> |
| --- | --- | --- |

## Analiza Riscului Contextual și Accesul Condiționat (Conditional Access)

Unul dintre obiectivele specifice ale temei de licență este implementarea unui sistem de analiză dinamică a parametrilor de autentificare.<sup>1</sup> Aceasta este diferența majoră între un VPN clasic și o soluție ZTNA modernă. În loc să fie o decizie binară (Permis/Respins), accesul devine adaptiv.<sup>2</sup>

### Algoritmul de Calcul al Scorului de Risc (Trust Score)

Sistemul va colecta o serie de „semnale" în momentul fiecărei cereri de acces și va calcula un scor numeric de încredere (0-100) <sup>1</sup>:

- **Locația Geografică (GeoIP):** Dacă accesul provine dintr-o regiune neobișnuită pentru utilizator (ex. altă țară), scorul de risc crește.<sup>1</sup>
- **Impossible Travel:** Dacă au trecut doar 10 minute de la ultimul login din București, iar acum cererea vine din Londra, sistemul detectează o anomalie fizică.<sup>2</sup>
- **Reputația IP-ului:** Verificarea adresei IP în baze de date de tip threat intelligence pentru a detecta noduri Tor, proxy-uri sau adrese compromise.<sup>13</sup>
- **Starea Dispozitivului (Postură):** Dacă agentul raportează că sistemul de operare nu are ultimele patch-uri de securitate instalate, scorul de încredere scade semnificativ.<sup>15</sup>
- **Ora și Comportamentul:** Logarea la ora 3 dimineața pentru un utilizator care lucrează de obicei între 9 și 18 reprezintă un semnal de risc.<sup>1</sup>

### Politici de Acces Condiționat

Pe baza scorului calculat, PDP-ul aplică politici de tip „Step-up Authentication" <sup>1</sup>:

| **Trust Score** | **Acțiune** | **Descriere** |
| --- | --- | --- |
| **90 - 100** | Grant Access | Acces direct (SSO) către resursele de bază.<sup>1</sup> |
| --- | --- | --- |
| **70 - 89** | Require MFA | Utilizatorul trebuie să valideze sesiunea prin WebAuthn (amprentă).<sup>1</sup> |
| --- | --- | --- |
| **40 - 69** | Limited Access | Acces doar la resurse non-critice (ex. email), blocat accesul la HR/Financiar.<sup>2</sup> |
| --- | --- | --- |
| **0 - 39** | Deny & Alert | Acces blocat complet, sesiune invalidată și alertă trimisă către administrator.<sup>1</sup> |
| --- | --- | --- |

## Evaluarea Posturii Dispozitivului (Device Posture Assessment)

În modelul Zero Trust, identitatea utilizatorului este doar jumătate din ecuație; cealaltă jumătate este identitatea și integritatea dispozitivului.<sup>15</sup> Un utilizator legitim care se conectează de pe un laptop infectat cu un keylogger reprezintă un risc inacceptabil.<sup>15</sup>

### Implementarea Verificărilor de Postură

Sistemul propus va utiliza un agent de endpoint care va interoga starea sistemului de operare folosind API-uri native (ex. WMI pe Windows sau interfețe /proc pe Linux).<sup>26</sup> Parametrii verificați includ <sup>15</sup>:

- **Versiunea OS:** Verificarea versiunii minime suportate și a prezenței patch-urilor critice.<sup>26</sup>
- **Antivirus/EDR:** Verificarea dacă un produs de securitate este activ și are definițiile la zi.<sup>15</sup>
- **Disk Encryption:** Asigurarea că hard-disk-ul este criptat (BitLocker/FileVault) pentru a proteja datele în caz de furt fizic.<sup>26</sup>
- **Firewall:** Verificarea activării firewall-ului local pe dispozitiv.<sup>15</sup>
- **Certificate de Mașină:** Verificarea prezenței unui certificat digital unic, emis de organizație, pentru a confirma că dispozitivul este unul gestionat (Managed Device).<sup>26</sup>

Această evaluare nu are loc doar la logare, ci este continuă. Dacă utilizatorul dezactivează firewall-ul în timpul sesiunii, agentul va raporta schimbarea, iar PDP-ul poate instrui instantaneu gateway-ul (PEP) să termine conexiunea WireGuard.<sup>2</sup>

## Plan de Implementare Pas cu Pas (Roadmap)

Pentru succesul proiectului de licență, implementarea trebuie să urmeze o structură logică, de la infrastructură la logică de afaceri.

### Faza 1: Pregătirea Infrastructurii și Containerizarea (Săptămânile 1-3)

Prima etapă constă în definirea mediului de dezvoltare și simularea rețelelor izolate folosind Docker.<sup>1</sup> Se vor crea două rețele virtuale în docker-compose.yml:

- public_net: Pentru comunicarea între client și Gateway.
- private_net: O rețea internă, fără acces la internet, unde vor locui serviciile de identitate și resursele.<sup>1</sup>

### Faza 2: Dezvoltarea Serviciului de Identitate și MFA (Săptămânile 4-6)

În această etapă se construiește „creierul" sistemului (PDP).<sup>1</sup>

- Implementarea API-urilor de înregistrare și login folosind FastAPI.
- Integrarea bibliotecii fido2 pentru a susține înregistrarea și verificarea cheilor WebAuthn.<sup>27</sup>
- Configurarea bazei de date PostgreSQL pentru stocarea credențialelor (hash-uite cu bcrypt) și a cheilor publice WebAuthn.<sup>1</sup>

### Faza 3: Implementarea Gateway-ului de Securitate și a Tunelului WireGuard (Săptămânile 7-9)

Aceasta este componenta cea mai tehnică, reprezentând PEP-ul.<sup>2</sup>

- Configurarea Nginx ca reverse proxy cu modulul auth_request.<sup>1</sup>
- Implementarea unui serviciu în Go sau Rust care utilizează biblioteca wgctrl pentru a activa/dezactiva dinamic peer-urile WireGuard în funcție de starea sesiunii.<sup>21</sup>
- Asigurarea comunicării securizate prin mTLS între Gateway și serviciul de autentificare.<sup>34</sup>

### Faza 4: Motorul de Risc și Agentul de Postură (Săptămânile 10-12)

Finalizarea logicii de Zero Trust.

- Dezvoltarea scriptului de postură (Endpoint Agent) care colectează datele de sistem.<sup>1</sup>
- Scrierea logicii de scoring în Python, integrând semnalele de IP, locație și postură.<sup>1</sup>
- Implementarea dashboard-ului de administrare unde pot fi vizualizate încercările de acces și scorurile de risc asociate.<sup>1</sup>

## Strategii de Testare și Evaluare

O soluție de securitate este validă doar dacă este testată riguros în condiții de stres și atac.

### Metodologia de Testare

Se vor utiliza scenarii de testare bazate pe vectori de atac reali <sup>1</sup>:

- **Testul Phishing:** Utilizarea unui domeniu similar pentru a încerca capturarea credențialelor. Rezultatul așteptat: WebAuthn trebuie să blocheze autentificarea.<sup>23</sup>
- **Testul Dispozitivului Compromis:** Tentativa de acces de pe un dispozitiv fără antivirus. Rezultatul așteptat: Scorul de risc scade sub pragul critic, iar accesul este refuzat.<sup>31</sup>
- **Testul Mișcării Laterale:** După logarea cu succes pe un cont de utilizator standard, se va încerca accesarea directă a resursei „HR" (protejată de o politică de acces mai strictă). Rezultatul așteptat: Sistemul trebuie să ceară o re-autentificare WebAuthn sau să blocheze accesul.<sup>11</sup>

### Evaluarea Performanței

Deoarece WireGuard este un protocol extrem de eficient, se vor măsura <sup>4</sup>:

- **Latența de stabilire a conexiunii (handshake).**
- **Throughput-ul de date** comparativ cu o conexiune necriptată.
- **Consumul de resurse (CPU/RAM)** la nivelul Gateway-ului pentru a demonstra eficiența implementării în Rust.<sup>9</sup>

## Concluzii și Perspective de Dezvoltare

Proiectarea unei soluții de acces distant conformă cu modelul Zero Trust reprezintă o provocare tehnică de anvergură, dar esențială în contextul amenințărilor cibernetice moderne.<sup>2</sup> Prin integrarea protocolului WireGuard cu autentificarea WebAuthn și un motor de risc dinamic, soluția propusă depășește limitările VPN-urilor tradiționale, oferind o protecție granulară, identitate-centrică și rezistentă la phishing.<sup>3</sup>

Această arhitectură nu doar că asigură o notă maximă prin complexitatea sa (utilizarea Rust, Go, microservicii, criptografie modernă), dar oferă și o bază solidă pentru dezvoltări ulterioare.<sup>1</sup> Perspectivele de viitor includ integrarea unor algoritmi de Machine Learning pentru detectarea proactivă a anomaliilor comportamentale, utilizarea eBPF pentru filtrarea pachetelor la viteze de ordinul nanosecundelor și extinderea sistemului către o arhitectură de tip „Mesh VPN" similară cu Tailscale sau NetBird.<sup>25</sup> În final, securitatea cibernetică este un proces continuu de adaptare, iar adoptarea principiilor Zero Trust este singura cale viabilă pentru a proteja resursele informaționale într-o lume digitală fără frontiere.<sup>3</sup>

#### Works cited

- ...txt
- ServiceNow Supports NIST 800-207 Zero-Trust Cybersecurity, accessed January 29, 2026, <https://www.servicenow.com/community/secops-articles/servicenow-supports-nist-800-207-zero-trust-cybersecurity/ta-p/3455669>
- Zero Trust Architecture - NIST Technical Series Publications, accessed January 29, 2026, <https://nvlpubs.nist.gov/nistpubs/specialpublications/NIST.SP.800-207.pdf>
- What Is WireGuard? - Palo Alto Networks, accessed January 29, 2026, <https://www.paloaltonetworks.com/cyberpedia/what-is-wireguard>
- Conditional Access: A Must-Have for Modern Security - AKA Identity, accessed January 29, 2026, <https://www.akaidentity.io/blog/conditional-access-a-must-have-for-modern-security>
- WebAuthn, Passwordless and FIDO2 Explained | Duo Security, accessed January 29, 2026, <https://duo.com/blog/webauthn-passwordless-fido2-explained-componens-passwordless-architecture>
- Passwordless Authentication with FIDO2 and WebAuthn | Frontegg, accessed January 29, 2026, <https://frontegg.com/guides/passwordless-authentication-with-fido2-and-webauthn>
- Beyond the Buzzword: Why the Policy Decision Point is the True Arbiter of Zero Trust - FRC, accessed January 29, 2026, <https://fedresources.com/beyond-the-buzzword-why-the-policy-decision-point-is-the-true-arbiter-of-zero-trust/>
- BoringTun, a userspace WireGuard implementation in Rust - The Cloudflare Blog, accessed January 29, 2026, <https://blog.cloudflare.com/boringtun-userspace-wireguard-rust/>
- Zero Trust Webinar: Transforming Cybersecurity - DAU, accessed January 29, 2026, <https://www.dau.edu/sites/default/files/Migrate/EventAttachments/797/DAU%20Zero%20Trust%20Voelker%20V1%20%2020230119.pdf>
- Zero Trust Starts Here: A Guide to Policy Enforcement Points - Trio MDM, accessed January 29, 2026, <https://www.trio.so/blog/policy-enforcement-point>
- Zero Trust Architecture - SP 800-207 - CSRC, accessed January 29, 2026, <https://csrc.nist.rip/publications/detail/sp/800-207/final>
- The Logical Components of Zero Trust - InterSec Inc., accessed January 29, 2026, <https://www.intersecinc.com/blogs/the-logical-components-of-zero-trust>
- NIST 800-207: Zero Trust Architecture | NextLabs, accessed January 29, 2026, <https://www.nextlabs.com/wp-content/uploads/2024/11/NextLabs-White-Paper-NIST-800-207-Zero-Trust-Architecture.pdf>
- Essentials of ZTNA - Device Posture - monitorapp, accessed January 29, 2026, <https://www.monitorapp.com/en/resources/blog/903>
- Conditional Access Policy Engine - Empower Your Security - SecurEnvoy, accessed January 29, 2026, <https://securenvoy.com/conditional-access-policy-engine/>
- What is WireGuard VPN protocol? All You Need to Know - NordLayer, accessed January 29, 2026, <https://nordlayer.com/learn/vpn/wireguard/>
- WireGuard: fast, modern, secure VPN tunnel, accessed January 29, 2026, <https://www.wireguard.com/>
- apognu/wgctl: Utility to configure and manage your WireGuard tunnels - GitHub, accessed January 29, 2026, <https://github.com/apognu/wgctl>
- Wireguard Rust Implementation - NLnet Foundation, accessed January 29, 2026, <https://nlnet.nl/project/Wireguard-Rust/>
- DefGuard/wireguard-rs: Rust library providing unified WireGuard interface to native/kernel and userspace implementations - GitHub, accessed January 29, 2026, <https://github.com/DefGuard/wireguard-rs>
- FIDO Authentication with WebAuthn - Auth0 Docs, accessed January 29, 2026, <https://auth0.com/docs/secure/multi-factor-authentication/fido-authentication-with-webauthn>
- WebAuthn Guide, accessed January 29, 2026, <https://webauthn.guide/>
- FIDO Metadata Service (MDS) Overview - FIDO Alliance, accessed January 29, 2026, <https://fidoalliance.org/metadata/>
- Building a Production-Ready Zero-Trust Network Access (ZTNA) System: A Complete Implementation Guide | by Himansu Saha | Medium, accessed January 29, 2026, <https://medium.com/@himansusaha/building-a-production-ready-zero-trust-network-access-ztna-system-a-complete-implementation-3672358fe4a5>
- Configuring Device Posture Profiles - Zscaler Help Portal, accessed January 29, 2026, <https://help.zscaler.com/zscaler-client-connector/configuring-device-posture-profiles>
- WebAuthn in the CLI - jfx's site, accessed January 29, 2026, <https://jfx.ac/blog/webauthn-in-the-cli/>
- duo-labs/py_webauthn: Pythonic WebAuthn - GitHub, accessed January 29, 2026, <https://github.com/duo-labs/py_webauthn>
- Conditional access policies | ManageEngine ADSelfService Plus, accessed January 29, 2026, <https://www.manageengine.com/products/self-service-password/conditional-access-policy.html>
- Microsoft Entra Conditional Access: Zero Trust Policy Engine, accessed January 29, 2026, <https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview>
- 5\. Device Posture Check for Zero Trust Network Access - Exium Academy, accessed January 29, 2026, <https://docs.exium.net/en/public/Briefs/ZTNA/Zero-Trust-Network-Access-Using-Device-Posture-Check>
- Basic ZTNA configuration | FortiGate / FortiOS 7.6.5 - Fortinet Document Library, accessed January 29, 2026, <https://docs.fortinet.com/document/fortigate/7.6.5/administration-guide/194961/basic-ztna-configuration>
- WireguardManager is a microservice that allows you to run a VPN server and manage peers through API. - GitHub, accessed January 29, 2026, <https://github.com/AkaCyberRat/WireguardManager>
- How to implement the zero trust principle in cloud native construction?, accessed January 29, 2026, <https://www.tencentcloud.com/techpedia/116507>
- defguard - Zero-Trust WireGuard® 2FA/MFA VPN, accessed January 29, 2026, <https://defguard.net/>
- NetBird - Open Source Zero Trust Networking, accessed January 29, 2026, <https://netbird.io/>
- JIT WireGuard - Hacker News, accessed January 29, 2026, <https://news.ycombinator.com/item?id=39688545>