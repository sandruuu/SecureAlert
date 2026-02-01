# SecureAlert - Zero Trust Network Access (ZTNA)

## Introducere

SecureAlert este o soluție de Zero Trust Network Access (ZTNA) care implementează principiul "never trust, always verify" (nu încrede niciodată, verifică întotdeauna). Spre deosebire de modelele tradiționale de securitate bazate pe perimetru, care presupun că utilizatorii din interiorul rețelei sunt de încredere, arhitectura Zero Trust tratează fiecare cerere de acces ca potențial suspectă și necesită verificare continuă a identității, dispozitivului și contextului.

Aplicația este concepută pentru a proteja resursele organizaționale prin autentificare multi-factor rezistentă la phishing, monitorizare continuă a stării de securitate a dispozitivelor și control adaptiv al accesului bazat pe un scor de încredere calculat dinamic.

---

## Arhitectura Sistemului

Sistemul este construit pe o arhitectură de microservicii containerizate, orchestrată prin Docker Compose. La baza arhitecturii se află principiul separării responsabilităților, unde fiecare componentă îndeplinește un rol specific în lanțul de securitate.

**Gateway-ul** reprezintă punctul unic de intrare în sistem și este implementat folosind Nginx ca reverse proxy. Toate cererile de la clienți, fie că provin din browser sau din agentul de postură, trec prin acest gateway care le direcționează către serviciul de autentificare. Această abordare permite implementarea centralizată a politicilor de securitate și oferă un singur punct de monitorizare pentru tot traficul.

**Serviciul de Autentificare** este inima sistemului și este construit folosind framework-ul FastAPI în Python. Acest serviciu gestionează întregul ciclu de viață al autentificării: înregistrarea utilizatorilor, autentificarea cu parolă sau WebAuthn, verificarea multi-factor, calculul scorului de risc și managementul sesiunilor. FastAPI a fost ales pentru performanța sa ridicată și suportul nativ pentru operațiuni asincrone, esențiale pentru gestionarea simultană a multiplelor cereri de autentificare.

**Baza de Date PostgreSQL** stochează toate informațiile persistente ale sistemului: utilizatori, dispozitive înregistrate, credențiale WebAuthn, jurnale de acces și evenimente de postură. Schema a fost proiectată pentru a suporta relațiile complexe dintre utilizatori și dispozitivele lor multiple, permițând urmărirea istoricului de securitate pentru fiecare combinație utilizator-dispozitiv.

**Serverul VPN WireGuard** oferă conectivitate securizată pentru dispozitivele autorizate. După ce un utilizator trece de toate verificările de securitate, sistemul poate genera automat configurații WireGuard personalizate, asigurând că doar dispozitivele verificate pot accesa resursele protejate prin tunelul VPN criptat.

---

## Componentele Frontend

Interfața utilizator este construită ca o aplicație single-page (SPA) folosind React și Vite ca bundler. Această abordare permite o experiență de utilizator fluidă și responsivă, fără reîncărcări complete ale paginii.

**Pagina de Autentificare** reprezintă punctul de intrare pentru toți utilizatorii și implementează un flux de autentificare adaptiv. Utilizatorii pot alege între autentificarea cu parolă sau autentificarea biometrică folosind WebAuthn (Windows Hello, Touch ID, sau chei de securitate hardware precum YubiKey). Pagina detectează automat dacă browser-ul suportă WebAuthn și oferă opțiunea corespunzătoare. După autentificarea primară, dacă scorul de risc indică necesitatea unui factor suplimentar, utilizatorul este redirecționat către verificarea MFA, care poate fi realizată prin cod TOTP (din aplicația Authenticator) sau prin cod trimis pe email.

**Dashboard-ul Utilizatorului** afișează informații despre dispozitivele înregistrate, starea curentă a conexiunii VPN și permite descărcarea configurației WireGuard pentru conectare. Utilizatorii pot vizualiza istoricul propriilor autentificări și pot gestiona setările de securitate ale contului, inclusiv activarea autentificării multi-factor TOTP.

**Panoul de Administrare** este accesibil doar utilizatorilor cu rol de administrator și oferă o vedere de ansamblu asupra întregului sistem. Administratorii pot crea utilizatori noi, trimite invitații de înregistrare, activa sau dezactiva conturi și vizualiza jurnalele de securitate. Interfața de administrare include o secțiune dedicată jurnalelor, care afișează atât evenimentele de autentificare (login-uri reușite, provocări MFA, accese blocate) cât și evenimentele de postură raportate de agenții client.

---

## Componentele Backend

**Routerul de Autentificare** gestionează toate operațiunile legate de identitate. Procesul de înregistrare începe când un administrator creează un utilizator nou și trimite un cod de invitație. Utilizatorul primește acest cod pe email și îl folosește pentru a-și completa înregistrarea, configurând simultan o metodă de autentificare (parolă sau WebAuthn). Procesul de login verifică credențialele, calculează scorul de risc bazat pe postură și context, și decide dacă accesul este permis direct, necesită MFA suplimentar, sau trebuie blocat complet.

**Motorul de Risc** reprezintă componenta centrală a arhitecturii Zero Trust și implementează calculul scorului de încredere. Acest scor este o valoare numerică între 0 și 100 care reflectă nivelul de încredere pe care sistemul îl are în autenticitatea și legitimitatea unei cereri de acces. Scorul este calculat ca o sumă ponderată a trei factori principali.

Postura dispozitivului contribuie cu 50% la scorul final și evaluează starea de securitate a dispozitivului client. Sistemul verifică dacă firewall-ul este activ pe toate profilele (privat, public, domeniu), dacă soluția antivirus (Windows Defender) funcționează cu protecție în timp real, și dacă versiunea sistemului de operare este suportată și actualizată.

Contextul contribuie cu 30% și analizează comportamentul de acces al utilizatorului. Principala verificare este detectarea călătoriei imposibile (impossible travel): dacă adresa IP a utilizatorului s-a schimbat semnificativ într-un interval de timp prea scurt pentru a fi fizic posibil, sistemul reduce scorul și poate declanșa verificări suplimentare.

Reputația IP-ului contribuie cu 20% și verifică dacă adresa IP de origine apare în listele cunoscute de adrese malițioase, proxy-uri anonime sau noduri Tor. O adresă IP cu reputație proastă poate duce la blocarea completă a accesului.

**Routerul de Administrare** expune funcționalitățile necesare gestionării utilizatorilor și monitorizării sistemului. Toate endpoint-urile sunt protejate de middleware-ul care verifică dacă utilizatorul curent are rol de administrator.

**Routerul Utilizator** oferă funcționalități pentru utilizatorii obișnuiți, inclusiv înregistrarea de dispozitive noi și, critic, endpoint-ul pentru raportarea posturii. Acest endpoint primește rapoartele de la agenții client, validează semnătura criptografică, și actualizează starea dispozitivului în baza de date.

---

## Agentul de Postură

Agentul de postură este o componentă software care rulează pe dispozitivul client și efectuează verificări periodice ale stării de securitate. Implementat ca script PowerShell pentru Windows, agentul colectează informații despre sistemul de operare, starea firewall-ului și statusul antivirusului, apoi transmite aceste date către backend într-un format securizat.

Fiecare dispozitiv înregistrat primește un secret unic stocat în baza de date. Agentul folosește acest secret pentru a genera semnături HMAC-SHA256 pentru fiecare raport de postură. Backend-ul verifică aceste semnături înainte de a procesa raportul, asigurând că datele nu pot fi falsificate de un atacator.

Pentru a preveni atacurile de tip replay, unde un atacator ar putea intercepta și retransmite un raport valid, sistemul implementează mai multe mecanisme de protecție. Fiecare raport include un timestamp Unix care trebuie să fie în intervalul de plus/minus 60 de secunde față de timpul serverului, și un nonce unic (UUID generat aleator) care nu poate fi refolosit. Serverul menține o listă a nonce-urilor utilizate recent și respinge orice raport care încearcă să refolosească un nonce.

La fiecare 30 de secunde, agentul colectează datele de postură, construiește raportul, generează semnătura și îl transmite backend-ului. Dacă backend-ul detectează o degradare a posturii care duce la un scor sub pragul de 60, toate sesiunile utilizatorului sunt invalidate instant. Agentul primește un răspuns de deconectare și afișează o notificare Windows care informează utilizatorul despre motivul terminării sesiunii.

---

## Fluxul de Autentificare

Când un utilizator încearcă să acceseze sistemul, fluxul de autentificare urmează o secvență bine definită de pași. Mai întâi, utilizatorul introduce numele de utilizator, iar sistemul verifică dacă contul există și este activ. Dacă utilizatorul a configurat WebAuthn, browser-ul primește o provocare criptografică care trebuie semnată cu cheia privată stocată pe dispozitivul de autentificare (cheie hardware, Windows Hello, sau Touch ID).

După verificarea cu succes a autentificării primare, sistemul interoghează baza de date pentru a obține ultimul raport de postură al dispozitivului și informațiile contextuale despre accesurile anterioare ale utilizatorului. Aceste date sunt transmise motorului de risc, care calculează scorul de încredere.

Dacă scorul depășește 80, utilizatorul este considerat de încredere ridicată și primește acces direct fără verificări suplimentare. Acest scenariu se aplică de obicei utilizatorilor care se autentifică de pe dispozitive cunoscute, cu postură de securitate bună, din locații obișnuite.

Dacă scorul se situează între 60 și 80, sistemul solicită un factor suplimentar de autentificare. Utilizatorului i se prezintă opțiunea de a introduce un cod TOTP din aplicația de autentificare sau de a primi un cod pe email. Această verificare suplimentară compensează incertitudinea indicată de scorul de risc moderat.

Dacă scorul este sub 60, accesul este blocat complet și evenimentul este înregistrat pentru investigare ulterioară de către administratori. Utilizatorul primește un mesaj care indică faptul că accesul a fost refuzat din motive de securitate.

---

## Fluxul de Monitorizare Continuă

Modelul Zero Trust nu se oprește la momentul autentificării. Monitorizarea continuă verifică periodic dacă condițiile care au permis accesul inițial sunt încă valide pe toată durata sesiunii.

După autentificarea cu succes, agentul de postură începe să transmită rapoarte la intervale regulate. Fiecare raport declanșează o recalculare a scorului de încredere. Dacă utilizatorul dezactivează firewall-ul, dezinstalează antivirusul, sau dacă sistemul detectează alte schimbări care afectează negativ postura de securitate, scorul va scădea.

Când scorul calculat scade sub pragul de 60, sistemul invalidează toate sesiunile active ale utilizatorului. Această invalidare se produce instant pe partea de server prin ștergerea token-urilor de sesiune din memoria serverului. Următoarea cerere de la browser-ul utilizatorului va primi un răspuns de neautorizat (401), iar utilizatorul va fi redirecționat către pagina de login.

Simultan, agentul primește un răspuns de deconectare care include motivul invalidării sesiunii. Agentul afișează o notificare Windows care informează utilizatorul că sesiunea a fost terminată și indică problema specifică (de exemplu, "Firewall dezactivat"). Această transparență ajută utilizatorul să înțeleagă ce acțiune a declanșat deconectarea și ce trebuie să corecteze pentru a restabili accesul.

---

## Mecanisme de Securitate

**Autentificarea Multi-Factor Rezistentă la Phishing** reprezintă prima linie de apărare a sistemului. WebAuthn (FIDO2) folosește criptografie cu cheie publică pentru a verifica identitatea utilizatorului fără a transmite vreodată secretul (cheia privată) prin rețea. Atacatorii nu pot replica credențialele chiar dacă interceptează traficul sau înșeală utilizatorul să acceseze un site fals.

**Semnarea Criptografică a Rapoartelor** asigură integritatea și autenticitatea datelor de postură. Fiecare dispozitiv are un secret unic, iar rapoartele sunt semnate folosind algoritmul HMAC-SHA256. Backend-ul poate verifica că raportul provine de la un dispozitiv legitim și nu a fost modificat în tranzit.

**Protecția Împotriva Atacurilor Replay** combină mai multe straturi de apărare. Timestamp-urile cu fereastră de validitate de 60 de secunde previn refolosirea rapoartelor vechi. Nonce-urile unice asigură că fiecare raport poate fi procesat o singură dată. Verificarea semnăturii HMAC garantează că atacatorul nu poate genera rapoarte false.

**Managementul Sesiunilor** folosește cookie-uri HTTP-only care nu pot fi accesate din JavaScript, protejând împotriva atacurilor XSS. Sesiunile sunt stocate pe partea de server, permițând invalidarea instantanee din orice locație fără a depinde de cooperarea clientului.

---

## Modelul de Date

Baza de date este structurată în jurul a patru entități principale care reflectă conceptele fundamentale ale sistemului.

**Utilizatorii** reprezintă persoanele care interacționează cu sistemul. Fiecare utilizator are un nume de utilizator unic, informații de profil, un hash al parolei (dacă folosește autentificare cu parolă), un rol care determină permisiunile, și configurații opționale pentru MFA (secretul TOTP).

**Dispozitivele** sunt asociate utilizatorilor și reprezentă echipamentele fizice de pe care aceștia accesează sistemul. Fiecare dispozitiv stochează cheia publică WireGuard, adresa IP VPN alocată, ultimul raport de postură, scorul de încredere curent, și secretul folosit pentru semnarea rapoartelor de postură.

**Credențialele WebAuthn** stochează cheile publice înregistrate pentru autentificarea biometrică. Un utilizator poate avea multiple credențiale (de exemplu, Windows Hello pe laptop și Touch ID pe telefon), și fiecare credențială include contorul de semnături pentru detecția clonării.

**Jurnalele de Acces și Evenimentele de Postură** păstrează istoricul complet al activității sistemului. Jurnalele de acces înregistrează fiecare încercare de autentificare cu rezultatul, scorul de risc la momentul respectiv, și informațiile contextuale (IP, user agent). Evenimentele de postură documentează schimbările în starea de securitate a dispozitivelor și deciziile de invalidare a sesiunilor.

---

## Infrastructura de Deployment

Aplicația este containerizată folosind Docker și orchestrată prin Docker Compose, permițând deployment consistent pe orice sistem care suportă containere. Configurația definește cinci servicii care comunică printr-o rețea Docker internă.

Gateway-ul Nginx este singurul serviciu expus extern, ascultând pe portul 8095. Configurația de reverse proxy direcționează cererile către frontend (pentru fișierele statice React) sau către backend (pentru endpoint-urile API prefixate cu /api/).

Serviciul de autentificare rulează pe o rețea internă și comunică cu baza de date PostgreSQL și cu serverul WireGuard. Volumele Docker montează codul sursă și fișierele de configurare, permițând dezvoltarea fără reconstrucția containerelor.

Baza de date PostgreSQL folosește un volum persistent pentru a păstra datele între restartări. Credențialele sunt configurate prin variabile de mediu definite în docker-compose.yml.

Serverul WireGuard este configurat pentru a accepta conexiuni VPN pe portul UDP 51820. Configurațiile peer-urilor sunt generate dinamic de serviciul de autentificare și stocate în volumul partajat wg_config.

---

## Considerații de Securitate

Arhitectura a fost proiectată cu principiul defense-in-depth (apărare pe mai multe straturi). Chiar dacă un atacator reușește să compromită o componentă, celelalte straturi de securitate limitează impactul atacului.

Comunicația între client și server folosește exclusiv HTTPS în producție, prevenind interceptarea traficului. Cookie-urile de sesiune sunt marcate ca HTTP-only și Secure, eliminând vectorii comuni de atac XSS și man-in-the-middle.

Parolele sunt stocate folosind PBKDF2 cu SHA-256, un algoritm de hash proiectat specific pentru rezistența la atacurile brute-force. Fiecare parolă are un salt unic, făcând imposibilă utilizarea tabelelor precompilate (rainbow tables).

Monitorizarea continuă asigură că compromiterea unui dispozitiv client este detectată rapid. Dacă un atacator reușește să instaleze malware pe dispozitivul utilizatorului, modificările în starea de securitate (dezactivarea antivirusului, de exemplu) vor declanșa deconectarea automată înainte ca atacatorul să poată exploata accesul.

Jurnalizarea completă a tuturor evenimentelor de securitate permite investigarea incidentelor și detectarea pattern-urilor de atac. Administratorii pot identifica încercări repetate de acces neautorizat, dispozitive compromise, sau comportamente anormale care ar putea indica un atac în desfășurare.
