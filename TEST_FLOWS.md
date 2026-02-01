# Fluxuri de Testare - SecureAlert ZTNA

## Cuprins
1. [Testare Rol Administrator](#1-testare-rol-administrator)
2. [Testare Rol Utilizator](#2-testare-rol-utilizator)
3. [Testare Agent Postură](#3-testare-agent-postură)
4. [Testare Scenarii de Securitate](#4-testare-scenarii-de-securitate)

---

## 1. Testare Rol Administrator

### Test 1.1: Autentificare Administrator

**Precondiții:** 
- Există un utilizator cu rol "admin" în baza de date
- Administratorul a primit codul de invitație și și-a înregistrat credențialele FIDO2

**Notă despre crearea primului administrator:**
Primul administrator este creat manual în baza de date sau printr-un script de inițializare. După crearea înregistrării, sistemul generează un cod de invitație care este afișat în consolă (logs) sau trimis pe email. Administratorul accesează pagina de înregistrare, introduce codul de invitație și configurează autentificarea FIDO2 (Windows Hello, cheie de securitate hardware, sau Touch ID).

**Pași pentru autentificare:**
1. Accesează `http://localhost:8095`
2. Introdu username-ul administratorului
3. Browser-ul afișează prompt-ul WebAuthn (Windows Hello / cheie de securitate)
4. Completează verificarea biometrică sau cu cheie hardware
5. Dacă scorul de risc este mediu (60-80), introdu codul MFA din email

**Rezultat așteptat:** Utilizatorul este redirecționat către `/admin/dashboard` și vede Dashboard-ul de Administrare cu secțiunile Overview, Users și System Logs în sidebar.

---

### Test 1.2: Creare Utilizator Nou

**Precondiții:** Administrator autentificat.

**Pași:**
1. Din sidebar, navighează la "Users"
2. Click pe butonul "Add User"
3. Completează formularul:
   - Username: `test.user@example.com`
   - Full Name: `Test User`
   - Role: `user`
4. Click "Create User"

**Rezultat așteptat:** 
- Apare mesaj de confirmare
- Utilizatorul nou apare în lista de utilizatori cu status "Inactive"
- Un email cu codul de invitație este trimis (verifică logs)

---

### Test 1.3: Dezactivare Utilizator

**Precondiții:** Administrator autentificat, există cel puțin un utilizator activ (altul decât administratorul curent).

**Pași:**
1. Din lista de utilizatori, identifică un utilizator activ
2. Click pe butonul de toggle status (sau "Deactivate")
3. Confirmă acțiunea

**Rezultat așteptat:**
- Status-ul utilizatorului se schimbă în "Inactive"
- Utilizatorul nu mai poate accesa sistemul
- Badge-ul de status se actualizează vizual

---

### Test 1.4: Ștergere Utilizator

**Precondiții:** Administrator autentificat, există un utilizator care poate fi șters.

**Pași:**
1. Din lista de utilizatori, identifică utilizatorul de șters
2. Click pe butonul "Delete"
3. Confirmă ștergerea

**Rezultat așteptat:**
- Utilizatorul dispare din listă
- Toate datele asociate (dispozitive, credențiale, logs) sunt șterse
- Nu se poate șterge propriul cont de administrator

---

### Test 1.5: Vizualizare Jurnale de Securitate

**Precondiții:** Administrator autentificat, există evenimente în sistem.

**Pași:**
1. Din sidebar, navighează la "System Logs"
2. Observă lista de evenimente
3. Folosește filtrele (ALL, AUTH, POSTURE)

**Rezultat așteptat:**
- Se afișează evenimentele în ordine cronologică inversă
- Fiecare eveniment arată: timestamp, sursă (AUTH/POSTURE), utilizator, acțiune, detalii, scor
- Filtrele funcționează corect
- Lista se actualizează automat la fiecare 5 secunde

---

### Test 1.6: Regenerare Invitație

**Precondiții:** Administrator autentificat, există un utilizator inactiv.

**Pași:**
1. Identifică un utilizator care nu și-a completat înregistrarea
2. Click pe "Reset Invite"
3. Notează noul cod de invitație

**Rezultat așteptat:**
- Se generează un nou cod de invitație
- Codul vechi este invalidat
- Un nou email este trimis utilizatorului

---

## 2. Testare Rol Utilizator

### Test 2.1: Înregistrare Utilizator Nou cu FIDO2

**Precondiții:** 
- Cod de invitație valid primit de la administrator pe email
- Dispozitiv cu suport WebAuthn (Windows Hello, Touch ID, sau cheie hardware)

**Cum primește utilizatorul codul de invitație:**
Administratorul creează utilizatorul din panoul de administrare (secțiunea Users → Add User). Sistemul generează automat un cod de invitație unic și îl trimite pe adresa de email specificată. Email-ul conține codul și instrucțiuni pentru finalizarea înregistrării.

**Pași:**
1. Accesează link-ul din email sau `http://localhost:8095`
2. Click pe "Register" 
3. Introdu username-ul (email-ul pentru care a fost creat contul)
4. Introdu codul de invitație din email
5. Browser-ul afișează prompt-ul WebAuthn pentru înregistrarea credențialelor
6. Completează verificarea biometrică (amprentă, recunoaștere facială) sau inserează cheia hardware
7. Finalizează înregistrarea

**Rezultat așteptat:** 
- Credențialele FIDO2 sunt înregistrate în baza de date
- Utilizatorul este redirecționat către pagina de login
- Statusul utilizatorului devine "Active" în panoul de administrare
- Utilizatorul poate accesa sistemul doar prin autentificare biometrică/FIDO2

---

### Test 2.2: Autentificare cu FIDO2 (WebAuthn)

**Precondiții:** Utilizator înregistrat cu credențiale FIDO2 configurate.

**Pași:**
1. Accesează pagina de login
2. Introdu username-ul
3. Browser-ul afișează automat prompt-ul WebAuthn
4. Completează verificarea biometrică sau folosește cheia hardware
5. Dacă scorul de risc este mediu (60-80), introdu codul MFA din email

**Rezultat așteptat:**
- Autentificare reușită prin FIDO2 (fără parolă)
- Redirecționare către User Dashboard
- Sesiune validă creată (cookie `session_id`)
- Log înregistrat cu scorul de risc calculat

---

### Test 2.3: Autentificare de pe Dispozitiv Nou

**Precondiții:** 
- Utilizator înregistrat cu FIDO2 pe un alt dispozitiv
- Dispozitiv nou cu suport WebAuthn

**Pași:**
1. Accesează pagina de login de pe dispozitivul nou
2. Introdu username-ul
3. Pentru autentificare cross-device, folosește cheia de securitate hardware (YubiKey) înregistrată anterior
4. SAU înregistrează noi credențiale pe acest dispozitiv după verificarea identității

**Rezultat așteptat:
- Browser-ul afișează prompt-ul WebAuthn
- După verificare, utilizatorul este autentificat
- Scorul de risc este calculat și afișat în logs

---

### Test 2.4: Activare MFA TOTP

**Precondiții:** Utilizator autentificat, fără MFA activ.

**Pași:**
1. Din User Dashboard, navighează la setările de securitate
2. Selectează "Enable TOTP"
3. Scanează codul QR cu o aplicație Authenticator
4. Introdu codul de verificare din aplicație
5. Confirmă activarea

**Rezultat așteptat:**
- MFA TOTP este activat pentru cont
- La următoarea autentificare, va fi solicitat codul TOTP
- Detaliile utilizatorului arată `MFA: Enabled`

---

### Test 2.5: Vizualizare Dashboard Utilizator

**Precondiții:** Utilizator autentificat.

**Pași:**
1. După autentificare, observă Dashboard-ul
2. Verifică secțiunile afișate

**Rezultat așteptat:**
- Se afișează informații despre dispozitivele înregistrate
- Se afișează starea conexiunii VPN
- Există opțiunea de a descărca configurația WireGuard

---

### Test 2.6: Logout

**Precondiții:** Utilizator autentificat.

**Pași:**
1. Click pe butonul de Logout din sidebar sau header
2. Confirmă acțiunea (dacă este necesar)

**Rezultat așteptat:**
- Sesiunea este invalidată pe server
- Utilizatorul este redirecționat la pagina de login
- Încercarea de a accesa pagini protejate rezultă în redirecționare la login

---

## 3. Testare Agent Postură

### Test 3.1: Pornire Agent cu Postură Bună

**Precondiții:** 
- Device ID și Device Secret obținute din baza de date
- Firewall activ pe toate profilele
- Windows Defender activ

**Pași:**
```powershell
.\posture_agent.ps1 -DeviceId "device-uuid" -DeviceSecret "device-secret" -BackendUrl "http://localhost:8095/api/user/posture/report"
```

**Rezultat așteptat:**
- Agentul pornește și afișează banner-ul
- La fiecare 30 secunde raportează: `Firewall: True, AV: True`
- Răspunsul este: `{"status": "ok", "score": 100}`

---

### Test 3.2: Degradare Postură - Dezactivare Firewall

**Precondiții:** Agent rulând cu postură bună.

**Pași:**
1. Într-o fereastră PowerShell separată (ca Administrator):
```powershell
netsh advfirewall set allprofiles state off
```
2. Așteaptă următorul raport de postură (max 30 secunde)

**Rezultat așteptat:**
- Agentul detectează firewall dezactivat
- Scorul scade sub 60
- Agentul primește: `{"status": "disconnect", "reason": "Trust score dropped to X..."}`
- Apare notificare Windows cu motivul deconectării
- Agentul se oprește

---

### Test 3.3: Verificare Invalidare Sesiune

**Precondiții:** 
- Utilizator autentificat în browser
- Agent rulând pentru același device

**Pași:**
1. Verifică că utilizatorul este autentificat în browser
2. Dezactivează firewall-ul (ca în Test 3.2)
3. Așteaptă raportul de postură și deconectarea
4. În browser, încearcă să faci refresh sau să navighezi

**Rezultat așteptat:**
- Sesiunea din browser este invalidată
- Utilizatorul primește eroare 401 și este redirecționat la login
- În Admin Logs apare eveniment `SESSION_TERMINATED`

---

### Test 3.4: Reactivare Postură

**Precondiții:** Firewall dezactivat din testul anterior.

**Pași:**
```powershell
netsh advfirewall set allprofiles state on
```

**Rezultat așteptat:**
- Firewall-ul este reactivat
- Utilizatorul se poate re-autentifica
- La rularea unui nou agent, rapoartele sunt acceptate

---

### Test 3.5: Testare Protecție Replay Attack

**Precondiții:** Agent rulând.

**Pași (Simulare manuală):**
1. Capturează un request valid de postură
2. Încearcă să retrimiți exact același request

**Rezultat așteptat:**
- Primul request este acceptat
- Al doilea request (identic) este respins cu: `{"detail": "Nonce already used (replay attack detected)"}`

---

### Test 3.6: Testare Timestamp Expirat

**Precondiții:** Device ID și Secret disponibile.

**Pași (Simulare manuală):**
1. Construiește un request cu timestamp vechi de mai mult de 60 secunde
2. Trimite requestul

**Rezultat așteptat:**
- Requestul este respins cu: `{"detail": "Timestamp expired or invalid"}`

---

## 4. Testare Scenarii de Securitate

### Test 4.1: Acces Blocat - Scor Sub 60

**Precondiții:** Dispozitiv cu postură proastă (firewall OFF, AV OFF).

**Pași:**
1. Încearcă să te autentifici de pe dispozitivul cu postură proastă

**Rezultat așteptat:**
- Scorul de risc calculat este sub 60
- Accesul este blocat cu mesaj: "Access Denied due to High Risk"
- În Admin Logs apare eveniment `BLOCKED`

---

### Test 4.2: MFA Step-Up - Scor 60-80

**Precondiții:** Dispozitiv cu postură parțială sau context suspect.

**Pași:**
1. Autentifică-te de pe un dispozitiv nou sau cu postură parțială
2. Observă că este solicitat MFA
3. Completează verificarea MFA

**Rezultat așteptat:**
- Sistemul detectează risc mediu
- Este solicitat cod MFA (TOTP sau Email)
- După verificare, accesul este acordat
- În Admin Logs apare eveniment `MFA_CHALLENGE` urmat de `LOGIN_SUCCESS`

---

### Test 4.3: Detecție Impossible Travel

**Precondiții:** Utilizator cu login recent.

**Pași:**
1. Autentifică-te de pe un IP
2. Așteaptă câteva minute
3. Autentifică-te din nou de pe un IP diferit (folosește VPN sau proxy)

**Rezultat așteptat:**
- Dacă schimbarea IP-ului a fost prea rapidă (sub 10 minute), scorul context scade
- Poate fi solicitat MFA suplimentar
- În logs apare warning despre "Impossible Travel"

---

### Test 4.4: IP în Blacklist

**Precondiții:** IP-ul clientului este în lista de IP-uri malițioase (THREAT_INTEL_BLACKLIST).

**Pași:**
1. Modifică temporar THREAT_INTEL_BLACKLIST în `risk_engine.py` pentru a include IP-ul de test
2. Încearcă autentificarea

**Rezultat așteptat:**
- Scorul este setat la 0 instant
- Accesul este blocat complet
- Mesaj: "Access Denied due to High Risk"

---

### Test 4.5: Semnătură HMAC Invalidă

**Precondiții:** Device ID valid, dar secret greșit.

**Pași:**
```powershell
.\posture_agent.ps1 -DeviceId "valid-id" -DeviceSecret "wrong-secret" -BackendUrl "http://localhost:8095/api/user/posture/report"
```

**Rezultat așteptat:**
- Requestul este respins cu: `{"detail": "Invalid signature"}`
- Agentul afișează eroare

---

### Test 4.6: WebAuthn pe Dispozitiv Necunoscut

**Precondiții:** Utilizator cu WebAuthn configurat pe un alt dispozitiv.

**Pași:**
1. Încearcă să te autentifici pe un dispozitiv nou unde nu ai înregistrat credențialele WebAuthn
2. Selectează opțiunea WebAuthn

**Rezultat așteptat:**
- Browser-ul cere verificarea dar nu găsește credențiale
- Utilizatorul primește eroare sau este redirecționat la autentificarea cu parolă

---

## Rezumat Teste

| Categorie | Test | Criticitate |
|-----------|------|-------------|
| Admin | 1.1 - Autentificare | Ridicată |
| Admin | 1.2 - Creare Utilizator | Ridicată |
| Admin | 1.3 - Dezactivare Utilizator | Medie |
| Admin | 1.4 - Ștergere Utilizator | Medie |
| Admin | 1.5 - Vizualizare Logs | Medie |
| Admin | 1.6 - Regenerare Invitație | Scăzută |
| User | 2.1 - Înregistrare FIDO2 | Ridicată |
| User | 2.2 - Login FIDO2 | Ridicată |
| User | 2.3 - Dispozitiv Nou | Ridicată |
| User | 2.4 - Activare MFA | Medie |
| User | 2.5 - Dashboard | Scăzută |
| User | 2.6 - Logout | Medie |
| Agent | 3.1 - Pornire | Ridicată |
| Agent | 3.2 - Degradare Postură | Ridicată |
| Agent | 3.3 - Invalidare Sesiune | Ridicată |
| Agent | 3.4 - Reactivare | Medie |
| Agent | 3.5 - Replay Protection | Ridicată |
| Agent | 3.6 - Timestamp | Ridicată |
| Security | 4.1 - Blocare Scor | Ridicată |
| Security | 4.2 - MFA Step-Up | Ridicată |
| Security | 4.3 - Impossible Travel | Medie |
| Security | 4.4 - IP Blacklist | Ridicată |
| Security | 4.5 - HMAC Invalid | Ridicată |
| Security | 4.6 - WebAuthn Necunoscut | Medie |
