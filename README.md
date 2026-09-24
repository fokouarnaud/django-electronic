# Labo d'électronique

Plateforme d'étude « façon Brilliant » pour apprendre et **maîtriser** les concepts d'électronique
(générateurs AC, loi de Faraday, bagues collectrices / bagues fendues, formes d'onde…).
Elle est **bilingue français / anglais** (français par défaut) et conçue pour tenir dans le
plan gratuit de PythonAnywhere (**500 Mo**).

- Django 5.2 LTS, SQLite (ORM uniquement, sans SQL brut : migration PostgreSQL possible plus tard)
- Admin [django-unfold](https://unfoldadmin.com/), interface Tailwind CSS v4 en mode sombre
- Développé en TDD : 180 tests `pytest`, couverture ≥ 95 % (mesurée : 98 %), lint `ruff`, CI GitHub Actions

---

## La routine d'étude

Chaque **concept** suit le même parcours, du livre jusqu'à la maîtrise :

1. **Lire** la section correspondante du livre d'Earl Boysen. Elle est référencée dans le concept
   (`ResourceLink` de type *book_section*) et s'affiche dans l'encart « Notes du livre ».
2. **Expliquer avec ses propres mots** : rédiger l'explication en Markdown, en français et en
   anglais (`clear_text_explanation_fr` / `_en`). Si la version anglaise est vide, le français
   est affiché.
3. **Expérimenter** dans le simulateur **Falstad** (`ResourceLink` de type *falstad_simulation*) :
   le circuit s'affiche dans un cadre responsive à côté du texte. Modifier les valeurs, observer
   les courbes.
4. **Enregistrer sa propre explication vidéo** avec **OBS**, la mettre sur **YouTube** (non
   répertoriée), puis coller l'URL dans `UserProgress.youtube_obs_embedded_url` (admin). Cette
   vidéo est **privée** : seul l'utilisateur concerné la voit, et elle passe avant les vidéos de
   référence (`ResourceLink` de type *youtube_reference*).
5. **S'auto-évaluer** avec le quiz : retour immédiat sur chaque réponse, puis explication.
   Un quiz réussi sans faute marque le concept comme **maîtrisé** ; le tableau de bord met sa
   progression à jour (`4 / 12 Concepts`).

Statuts d'un concept : `draft` (brouillon) → `review` (en révision) → `mastered` (maîtrisé).

### Saisir le contenu (admin Unfold, `/admin/`)

| Objet | Où | Remarques |
|---|---|---|
| Chapitre | *Chapters* | champs FR / EN groupés ; le slug est prérempli depuis le titre FR ; les concepts se modifient en ligne |
| Concept | *Concepts* | statut et ordre modifiables directement dans la liste ; ressources et flashcards en ligne |
| Ressource | dans le concept | types : `book_section`, `youtube_reference`, `falstad_simulation` |
| Flashcard + réponses | *Flashcards* | les réponses (`Choice`) se saisissent en ligne, `is_correct` marque la bonne |
| Progression / vidéo OBS | *User progress* | une ligne par utilisateur et par concept |

Seuls les hôtes **falstad.com** et **YouTube** sont intégrés en iframe ; toute autre URL de
simulation ou de vidéo est ignorée, jamais affichée.

---

## Démarrage en local

Prérequis : Python 3.10 – 3.13 (le code reste compatible avec PythonAnywhere). **Node.js n'est pas
nécessaire** : Tailwind s'exécute via le binaire autonome.

```bash
git clone <url-du-depot> django-electronic && cd django-electronic
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell : .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

cp .env.example .env                 # puis renseigner DJANGO_SECRET_KEY (facultatif en dev)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver           # http://127.0.0.1:8000/  ->  /fr/
```

`manage.py` utilise `config.settings.development` par défaut (DEBUG activé, rechargement du navigateur).

### Compiler le CSS Tailwind (binaire autonome, sans Node)

```bash
python manage.py tailwind build      # CSS minifié -> theme/static/css/dist/styles.css
python manage.py tailwind start      # mode watch pendant le développement
```

Le premier appel télécharge le binaire Tailwind v4 (hors dépôt, hors `node_modules`). La source
est `theme/static_src/src/styles.css` ; Tailwind lit les classes dans les gabarits HTML, le JS et
le Python. **Le CSS compilé est versionné** : la production n'a donc besoin ni de Node ni de
Tailwind. Recompilez et committez le fichier après toute modification de classes.

### Traductions (FR / EN)

Toutes les chaînes de l'interface passent par `{% trans %}`, `{% blocktrans %}` ou `_()`.
Le contenu dynamique (titres, descriptions, explications, questions) est stocké dans des colonnes
`*_fr` / `*_en` avec repli automatique sur l'autre langue.

```bash
# 1. ajouter/modifier les entrées dans locale/fr/LC_MESSAGES/django.po
#    (et l'entrée vide correspondante dans locale/en/LC_MESSAGES/django.po)
# 2. compiler les .po en .mo avec polib (aucun GNU gettext requis, pratique sous Windows)
python scripts/compile_messages.py
```

Les fichiers `.mo` sont **versionnés** : PythonAnywhere n'a pas besoin de `gettext`.
Si `msgfmt` est installé, `python manage.py compilemessages` est équivalent.

La langue est portée par l'URL (`/fr/…`, `/en/…`). Le sélecteur de la barre de navigation utilise
la vue native `set_language` (`/i18n/setlang/`) et vous garde sur la même page dans l'autre langue.

### Tests, lint, couverture

```bash
pytest -v                            # configuration de développement (config.settings.development)
pytest --cov                         # + couverture (la CI exige au moins 95 %)
ruff check . && ruff format --check . # lint + formatage (config dans pyproject.toml)
python manage.py makemigrations --check --dry-run   # aucune migration oubliée
```

La CI (`.github/workflows/ci.yml`) rejoue tout cela sous Python 3.10 et 3.13 (les bornes de
PythonAnywhere), puis `collectstatic`, `check --deploy` et la suite complète **en réglages de
production**. Toute nouvelle dépréciation Django 6.0 fait échouer les tests (`pytest.ini`).

### Simuler la production en local

```bash
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')"
python manage.py collectstatic --noinput --settings=config.settings.production
python manage.py check --deploy --settings=config.settings.production
pytest --ds=config.settings.production -q
```

`collectstatic` produit des fichiers **hachés et compressés (gzip)** dans `staticfiles/`
(≈ 9 Mo avec l'admin Unfold, dont le CSS de l'application : 35 Ko, 7 Ko compressé). Il signale
trois fichiers `admin/js/*` « déjà collectés » : c'est normal, Unfold remplace ceux de Django.
`check --deploy` ne remonte que deux avertissements volontaires : HSTS et la redirection HTTPS
sont **optionnels** (voir ci-dessous).

---

## Configuration : réglages séparés + variables d'environnement

```
config/settings/
├── base.py         # commun : apps, SQLite, i18n, fuseau Europe/Paris, Unfold, django-environ
├── development.py  # DEBUG=True, stockage statique simple, django-tailwind, browser-reload
└── production.py   # DEBUG=False, WhiteNoise compressé, durcissement sécurité, ALLOWED_HOSTS
```

`base.py` charge `environ.Env()` puis le fichier `.env` local (ignoré par git) ; les variables
d'environnement réelles restent prioritaires.

| Variable | Rôle | Défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | clé secrète. **Obligatoire en production** (le démarrage échoue sans elle ou avec la clé de dev) | clé de dev, refusée en prod |
| `DJANGO_ALLOWED_HOSTS` | hôtes supplémentaires, séparés par des virgules (ex. votre domaine) | vide |
| `DJANGO_SSL_REDIRECT` | `1` pour rediriger HTTP vers HTTPS | `0` |
| `DJANGO_HSTS_SECONDS` | durée HSTS (à activer une fois le HTTPS validé ; c'est irréversible côté navigateur) | `0` |
| `DATABASE_URL` | base de données (ex. `postgres://user:mdp@hôte:5432/nom` + `pip install "psycopg[binary]"`) | SQLite `./db.sqlite3` |
| `DJANGO_ADMIN_URL` | chemin de l'admin (un chemin moins prévisible limite les tentatives de connexion automatisées) | `admin/` |
| `DJANGO_ENV_FILE` | chemin d'un autre fichier `.env` | `./.env` |

Production : `DEBUG=False`, `ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.pythonanywhere.com']`
(+ variable ci-dessus), cookies de session et CSRF `Secure`, cookie de session `HttpOnly`,
`X-Frame-Options: DENY`, `nosniff`, en-tête proxy `X-Forwarded-Proto` reconnu, WhiteNoise
(`CompressedManifestStaticFilesStorage`) placé juste après `SecurityMiddleware`, journalisation
des erreurs sur la sortie d'erreur (visible dans l'*error log* de PythonAnywhere), pages `404` et
`500` personnalisées (la 500 est autonome : ni base, ni fichiers statiques).

Dépendances **épinglées** (`==`) pour des déploiements reproductibles : `requirements.txt`
(production, minimal : Django, unfold, django-environ, whitenoise, Markdown) et
`requirements-dev.txt` (+ django-tailwind, polib, pytest, pytest-cov, ruff…). Mettre à jour une
version = modifier la ligne puis relancer la suite.

---

## Structure

```
apps/curriculum/    modèles, vues, URLs, templatetags, embeds.py (iframes sûres), progress.py
  templates/ static/curriculum/quiz.js, magnetic.js
config/settings/    base / development / production
theme/              gabarit de base + CSS Tailwind compilé (theme/static/css/dist/)
locale/{fr,en}/     .po et .mo (versionnés)
scripts/            compile_messages.py
tests/              i18n, modèles, admin, saisie, accueil, pages, quiz, concept, progression, production
```

| URL | Rôle |
|---|---|
| `/fr/`, `/en/` | tableau de bord Bento (chapitres → concepts, statistiques) |
| `/<lang>/chapters/<chapitre>/concepts/<concept>/` | page du concept (explication, Falstad, vidéo) |
| `…/quiz/` | quiz du concept |
| `…/complete/` | POST (CSRF) : enregistre un quiz réussi |
| `/admin/` | administration Unfold |

Progression : utilisateurs connectés → table `UserProgress` ; visiteurs anonymes → session.

## Budget disque (mesuré)

| Élément | Taille |
|---|---|
| virtualenv de production (9 paquets) | ≈ 60 Mo |
| `staticfiles/` (après `collectstatic`) | ≈ 9 Mo |
| dépôt (fichiers suivis + historique) | < 1 Mo |
| **Total** | **≈ 70 Mo sur 500 Mo** |

---

## Déploiement sur PythonAnywhere (plan gratuit)

Avant de pousser, en local : `python manage.py tailwind build`, `python scripts/compile_messages.py`,
`pytest`, puis committez **le CSS compilé et les fichiers `.mo`**.

```bash
# ─── 1. Console Bash PythonAnywhere ────────────────────────────────────────────
cd ~
git clone <url-du-depot> django-electronic     # le CSS Tailwind compilé et les .mo sont déjà commités :
cd django-electronic                           #   ni Node.js, ni npm, ni gettext à installer ici

# ─── 2. virtualenv (Python 3.10 – 3.13, selon ce que propose PythonAnywhere) ────
mkvirtualenv --python=/usr/bin/python3.12 electronics     # s'active automatiquement
pip install -r requirements.txt                           # production uniquement (~60 Mo)
# plus tard : workon electronics

# ─── 3. Secrets : fichier .env (ignoré par git), lu par la console ET par le site ─
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
nano .env                                      # DJANGO_SECRET_KEY=<la clé générée>
chmod 600 .env

# ─── 4. Base de données et fichiers statiques ──────────────────────────────────
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput       # CSS + JS hachés et compressés dans staticfiles/
python manage.py check --deploy                # deux avertissements attendus : HSTS et redirection HTTPS
```

**Onglet *Web*** : *Add a new web app* → *Manual configuration* → même version de Python que le
virtualenv, puis renseignez :

| Champ | Valeur |
|---|---|
| Source code | `/home/VOTRE_USER/django-electronic` |
| Working directory | `/home/VOTRE_USER/django-electronic` |
| Virtualenv | `/home/VOTRE_USER/.virtualenvs/electronics` |
| Force HTTPS | activé |

Aucun mappage *Static files* n'est nécessaire : WhiteNoise sert `staticfiles/`.

Cliquez sur le lien du **fichier WSGI** (`/var/www/VOTRE_USER_pythonanywhere_com_wsgi.py`),
**remplacez tout son contenu** par :

```python
import os
import sys

path = "/home/VOTRE_USER/django-electronic"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.production"  # la clé secrète vient du .env

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
```

Sauvegardez, puis **Reload** sur l'onglet *Web* : le site est en ligne sur
`https://VOTRE_USER.pythonanywhere.com/` (redirigé vers `/fr/`).

```bash
# ─── Mise à jour ultérieure ────────────────────────────────────────────────────
cd ~/django-electronic && workon electronics
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# puis « Reload » dans l'onglet Web
```

Notes : sur le plan gratuit, il faut renouveler l'application (bouton de l'onglet *Web*) tous les
trois mois. `db.sqlite3` n'est pas dans git : sauvegardez-le avec `cp db.sqlite3 ~/backup-$(date +%F).sqlite3`.
Pour ajouter votre propre domaine, ajoutez-le à `DJANGO_ALLOWED_HOSTS` dans `.env`.

---

## Limites connues

- Les réponses du quiz sont vérifiées **côté navigateur** : outil d'étude personnel, pas d'examen noté.
- Pas encore de page de connexion publique (connexion via `/admin/`) ; la progression anonyme
  (session) n'est pas fusionnée dans la base à la connexion.

## Licence

Voir [LICENSE](LICENSE).
