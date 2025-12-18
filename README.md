Le projet s’appuie sur Cerebras Cloud pour exécuter certaines étapes de traitement (LLM).
Pour que l’application fonctionne correctement, il faut :

— créer un compte Cerebras ;
— générer une clé API ;
— renseigner cette clé dans le code ;
— démarrer l’application web (Django).

       Création du compte Cerebras
1. Ouvrez le site officiel : https://www.cerebras.net/
2. Accédez à la partie Cerebras Cloud puis créez un compte.
3. Validez votre adresse e-mail et connectez-vous au tableau de bord.
        Récupération de la clé API
        
1. Dans le tableau de bord Cerebras Cloud, allez dans la section API Keys (ou Developer
Settings).
2. Créez une nouvelle clé (Create New API Key).
3. Copiez la clé générée et gardez-la à portée de main.

        Insertion de la clé dans le code
        
Dans ce projet, la clé est renseignée directement dans un fichier Python.
Étapes
1. Ouvrez le fichier :
Modeldetraductionfinale(1).py
2. Rendez-vous vers la ligne 20 (l’emplacement peut varier légèrement).
3. Repérez la variable DEFAULT_CEREBRAS_API_KEY et remplacez sa valeur par votre clé.



        Démarrer l’application web (Django)
Une fois la clé insérée, lancez le serveur de développement Django.

1. Ouvrez un terminal.
2. Placez-vous dans le dossier racine du projet (là où se trouve manage.py).
3. Exécutez :
python manage.py runserver
4. Ouvrez ensuite votre navigateur à l’adresse :
http://127.0.0.1:8000/
