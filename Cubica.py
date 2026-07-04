from sqlalchemy import except_
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

from Bin import recipe
import ResourcePacks
import json
# On définit les variables en global pour qu'elles soient accessibles partout
import sys

# Valeur par defaut si le jeu est lance sans le launcher
pseudo_joueur = "Player"

# On verifie si le launcher a passe le pseudo en argument (sys.argv[1])
if len(sys.argv) > 1:
    pseudo_joueur = sys.argv[1]
    print("Jeu : Pseudo charge avec succes : " + str(pseudo_joueur))
else:
    print("Jeu : Aucun pseudo transmis, utilisation du nom par defaut")

# -----------------------------------------------------------------
# Ton code de jeu Cubica (app = Ursina(), etc.) commence ici...
# Tu peux utiliser la variable pseudo_joueur partout dans ton jeu !
# -----------------------------------------------------------------

# -----------------------------------------------------------------
# Ton code de jeu Cubica (app = Ursina(), etc.) commence ici...
# -----------------------------------------------------------------

# Tu peux maintenant utiliser la variable pseudo_joueur partout dans ton jeu !
player = None
main_menu = None
hand = None
selected_slot = 0
inventory_slots = []
loaded_modules = {}
title_text = None
play_button = None
game_ui = None  # Le parent de toute l'UI en jeu
recipes = recipe.recipes
craft_input_1 = None
craft_input_2 = None
craft_output = None
crafting_ui = None
epppliatcztdfftdfetg = None
arriereplan = None
filePath = 'Assets/items.cbdata'
CHUNK_SIZE = 8
RENDER_DISTANCE = 1 # Rayon de chunks chargés autour du joueur
chunks = {} # {(cx, cz): [liste_des_voxels]}
# Statistiques du joueur
player_hp = 20
player_max_hp = 20
last_player_damaged_time = 0
PLAYER_DAMAGED_COOLDOWN = 1.0  # Le joueur ne peut prendre des degats qu'une fois par seconde
regen_timer = 0
REGEN_COOLDOWN = 4.0  # Le joueur recupere de la vie toutes les 4 secondes
REGEN_AMOUNT = 1      # Il recupere 1 demi-coeur (1 point de PV) a chaque fois
try:
    with open(filePath, "r") as f:
        # On nettoie chaque ligne (strip) pour enlever les espaces et \n
        item_list = [line.strip().lower() for line in f.readlines()]
except FileNotFoundError:
    item_list = [] # Au cas où le fichier manque

block_properties = {}

def printf(**kwargs):
    """printf() est l'équivalent de print(f{message})"""
    print(f**kwargs)

class ScrollingPane(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Le Masque : la fenetre visible du shop
        self.mask = Entity(
            parent=self,
            model='quad',
            scale=(0.3, 0.45),
            color=color.black66,
            collider='box',
            z=0
        )

        # Le Conteneur : il porte les boutons
        self.container = Entity(parent=self.mask, z=-0.01)

        # Variables de controle
        self.container.y = 0.4  # Position de depart (haut)
        self.scroll_speed = 0.2  # Vitesse du scroll
        self.min_y = 0  # Limite pour ne pas monter trop haut
        self.max_y = 0.4  # Limite pour ne pas descendre trop bas

    def input(self, key):
        # On detecte la molette uniquement si on survol le shop
        if self.mask.hovered:
            # SCROLL VERS LE BAS (on fait monter le conteneur)
            if key == 'scroll down':
                self.container.y += self.scroll_speed

            # SCROLL VERS LE HAUT (on fait descendre le conteneur)
            if key == 'scroll up':
                self.container.y -= self.scroll_speed

            # Application des limites de securite
            self.container.y = clamp(self.container.y, self.min_y, self.max_y)

    def update(self):
        # SYSTEME DE DESACTIVATION (CLIPPING)
        # On boucle sur chaque bouton dans le conteneur
        for item in self.container.children:
            # Calcul de la position relative au masque
            # Si le bouton depasse les bordures haut (0.22) ou bas (-0.22) du masque
            pos_relative = item.y + self.container.y
            if pos_relative > 0.25 or pos_relative < -0.25:
                item.enabled = False
            else:
                item.enabled = True
def update_item_tooltip():
    # On récupère l'item actuellement sélectionné dans la main du joueur
    # Supposons que tu as une variable 'hand' ou que tu lis le slot actif
    current_item = inventory_slots[selected_slot].item_name

    if current_item:
        # On utilise ta fonction formatWord pour un affichage propre
        item_tooltip.text = formatWord(current_item)
        item_tooltip.enabled = True
    else:
        item_tooltip.enabled = False
import locale
from deep_translator import GoogleTranslator
def translateAuto(text):
    try:
        system_locale = locale.getdefaultlocale()[0]
        target_lang = system_locale.split('_')[0] if system_locale else 'en'
        translator = GoogleTranslator(source='auto', target=target_lang)
        translation = translator.translate(text)
        return translation
    except Exception as e:
        return f"Erreur lors de la traduction : {e}"
def translate(text, lang="en"):
    try:
        system_locale = locale.getdefaultlocale()[0]
        target_lang = system_locale.split('_')[0] if system_locale else 'en'
        translator = GoogleTranslator(source=lang, target=target_lang)
        translation = translator.translate(text)
        return translation
    except Exception as e:
        return f"Erreur lors de la traduction : {e}"

def formatWord(word):
    if not word:
        return ""
    formatted = word.replace("-", " ")
    return formatted.capitalize()
def Onmenu_ok():
    global _on_menu_
    _on_menu_ = True
def Onmenu_disok():
    global _on_menu_
    _on_menu_ = False
def update_chunks():
    if not player: return

    current_cx = math.floor(player.x / CHUNK_SIZE)
    current_cz = math.floor(player.z / CHUNK_SIZE)

    for cx in range(current_cx - RENDER_DISTANCE, current_cx + RENDER_DISTANCE + 1):
        for cz in range(current_cz - RENDER_DISTANCE, current_cz + RENDER_DISTANCE + 1):
            # ON AJOUTE CETTE VÉRIFICATION : Si le chunk n'est pas dans le dico, on le crée
            if (cx, cz) not in chunks:
                render_chunk(cx, cz)

def ifitem(name):
    # On s'assure que name n'est pas None avant de chercher
    if name is None:
        return False
    # Vérifie si le nom (en minuscule) est dans ta liste d'items
    return name.lower() in item_list


def getSizeFrom(name):
    # 1. On vérifie d'abord les cas vides ou la main
    if name == 'hand' or name == None or name == '':
        return (0.1, 0.25, 0.1)

    # 2. On vérifie si c'est un item spécial (ton épaisseur ultra fine)
    if ifitem(name):
        # Note : une valeur aussi petite risque de créer des bugs d'affichage (Z-fighting)
        # 0.001 est souvent suffisant pour paraître plat
        return (0.2, 0.2, 0.0001)

        # 3. Par défaut (pour les blocs classiques)
    return (0.2, 0.2, 0.2)


def setSizeFrom():
    global hand, selected_slot, inventory_slots

    # 1. On récupère l'objet Slot correspondant à l'index sélectionné
    current_slot = inventory_slots[selected_slot]

    # 2. On récupère le nom de l'item (ou "" si vide)
    item_name = current_slot.item_name if not current_slot.is_empty else ""

    # 3. On applique la taille et la texture à l'entité 'hand'
    # Attention : dans Ursina, on utilise 'scale', pas 'size'
    hand.scale = getSizeFrom(item_name)

    # On met la texture de l'item, ou la texture de la main par défaut
    if item_name == "" or item_name == "hand":
        hand.texture = 'Assets/BaseTextures/hand.png'
    else:
        hand.texture = current_slot.texture


def render_chunk(cx, cz):
    # Initialise le chunk dans le dictionnaire IMMÉDIATEMENT pour bloquer les autres appels
    chunks[(cx, cz)] = []

    x_min, x_max = cx * CHUNK_SIZE, (cx + 1) * CHUNK_SIZE
    z_min, z_max = cz * CHUNK_SIZE, (cz + 1) * CHUNK_SIZE

    # On limite la recherche à la taille du monde (ex: 50x50)
    for x in range(x_min, x_max):
        if x < 0 or x >= 50: continue  # Remplace 50 par ta variable WORLD_SIZE
        for z in range(z_min, z_max):
            if z < 0 or z >= 50: continue

            for y in range(10, -21, -1):
                if (x, y, z) in world_data:
                    v = Voxel(position=(x, y, z), name=world_data[(x, y, z)])
                    v.loaded = True
                    chunks[(cx, cz)].append(v)
                    break
def load_block_properties():
    path = 'Assets/break.cbdata'
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                # On cherche les lignes qui contiennent des données (on ignore les { et })
                if 'name=' in line:
                    # On nettoie la ligne et on sépare les infos
                    content = line.strip().replace('{', '').replace('}', '').replace(',', '')
                    parts = content.split(' ')

                    # Extraction des valeurs
                    props = {}
                    for p in parts:
                        if '=' in p:  # On vérifie qu'il y a bien une clé et une valeur
                            key, val = p.split('=')
                            # --- CONVERSION INTELLIGENTE ---
                            if val == 'True':
                                val = True
                            elif val == 'False':
                                val = False
                            elif '.' in val:  # Si y'a un point, c'est un float (0.5, 2.5...)
                                try:
                                    val = float(val)
                                except:
                                    val = val.replace("'", "")
                            elif val.isdigit():  # Si c'est un nombre entier
                                val = int(val)
                            else:
                                val = val.replace("'", "")  # C'est du texte
                            props[key] = val
                    # On stocke dans le dictionnaire avec le nom du bloc comme clé
                    block_properties[props['name']] = props
    except FileNotFoundError:
        print("Fichier break.cbdata introuvable !")


# On lance le chargement
load_block_properties()
def newworld(w):
    destroy(w)
    global main_menu, player, crosshair, worldexist
    worldexist = False
    # 0. Fermer le menu et activer les contrôles de base
    game_ui.enabled = True
    mouse.locked = True
    mouse.visible = False
    player.enabled = True
    if crosshair:
        crosshair.visible = True
    update_hearts_display()
    update_hotbar()

    generate_optimized_world(20, random.randint(1, 9999999999999999999))
worldexist = None
worldpath = ""
class Container(Entity):
    def __init__(self):
        super().__init__(
            enabled=True,
            parent=camera.ui
        )
        self.en = self.enabled
def loadGameMenu():
    """
    Cree un menu avec ton propre ScrollingPane pour lister et scroller les sauvegardes.
    """
    import os
    global main_menu, worldexist, worldpath

    # 1. On cree l entite principale du menu
    save_menu = Entity(parent=camera.ui, enabled=True)

    # Titre du menu
    Text(parent=save_menu, text="Play", y=0.3, origin=(0, 0), scale=2)

    # 2. On instancie TON ScrollingPane personnalisé
    # On le positionne un peu plus bas pour laisser de la place au titre
    scroll_pane = ScrollingPane(parent=save_menu, y=-0.05)

    if not os.path.exists("Saves"):
        os.makedirs("Saves")

    fichiers = [f for f in os.listdir("Saves") if f.endswith(".py")]
    Button(
        parent=scroll_pane.container,  # IMPORTANT : On l attache au conteneur qui bouge
        text="Generate World",
        y=0.15,  # Alignement vertical des fichiers
        scale=(0.25, 0.08),  # Taille adaptée pour tenir dans le masque
        color=color.green,
        on_click=lambda: newworld(save_menu)
    )
    if not fichiers:
        Text(parent=scroll_pane.container, text="Not save found", y=0, origin=(0, 0), color=color.gray)
        worldexist = False
    else:
        # 3. On ajoute les boutons directement dans le .container de ton ScrollingPane

        worldexist = True
        for i, f in enumerate(fichiers):
            nom_affichage = f[:-3]  # Enleve le .py pour l affichage
            chemin_complet = f"Saves/{f}"
            namee = f[:-3]

            Button(
                parent=scroll_pane.container,  # IMPORTANT : On l attache au conteneur qui bouge
                text=nom_affichage,
                y=0.15 - ((i + 1) * 0.12),  # Alignement vertical des fichiers
                scale=(0.25, 0.08),  # Taille adaptée pour tenir dans le masque
                color=color.azure,
                on_click=lambda path=chemin_complet: [loadGame(path, save_menu, namee)]
            )

        # 4. Ajustement dynamique des limites de scroll (optionnel mais utile)
        # Plus il y a de fichiers, plus le conteneur peut monter haut
        scroll_pane.max_y = max(0.4, (len(fichiers) * 0.12) - 0.2)

    # 5. Bouton Retour pour quitter ce menu
is_saving_now = False


def popup():
    mouse.locked = False
    mouse.visible = True
    if player:
        player.enabled = False
    if crosshair:
        crosshair.visible = False

    save_panel = WindowPanel(
        title='Nom du monde',
        content=(
            Text('Entrez le nom du monde:'),
            InputField(name='world_name_input', default_value='MonMonde'),
            Button(text='Sauvegarder', on_click=lambda: save(save_panel.content[1].text))
        )
    )
    # --- Réactiver le jeu après la fermeture ---
    mouse.locked = True
    mouse.visible = False
    if player:
        player.enabled = True
    if crosshair:
        crosshair.visible = True

        def save(iteeeeeee):
            global nom_sauvegarde
            nom_sauvegarde = iteeeeeee


custom_save_ui = []  # Liste pour tout détruire d'un coup
input_field = None
nom_sauvegarde = ""
def getface():
    """
    Renvoie le cote du bloc vise par la souris (right, left, front, back, top, bottom)
    en se basant sur la normale de la face survolee.
    """
    # Si la souris ne pointe sur aucun bloc, on ne peut pas s accrocher
    if not mouse.hovered_entity:
        return "none"

    # Recuperation du vecteur normal de la face ciblee
    normale = mouse.normal

    # Verification de l axe X (Gauche ou Droite)
    if normale.x > 0.5:
        return "left"
    if normale.x < -0.5:
        return "right"

    # Verification de l axe Z (Devant ou Derriere)
    if normale.z > 0.5:
        return "back"
    if normale.z < -0.5:
        return "front"

    # Verification de l axe Y (Haut ou Bas)
    if normale.y > 0.5:
        return "top"
    if normale.y < -0.5:
        return "bottom"

    return "none"
def saveGame():
    global custom_save_ui, input_field
    global main_menu, worldexist, worldpath, is_saving_now, nom_sauvegarde, play_button
    main_menu.enabled = False
    main_menu.visible = False
    print(str(worldexist) + ", " + str(worldpath) + ", " + str(nom_sauvegarde))

    # On fige le jeu
    mouse.locked = False
    mouse.visible = True
    player.enabled = False
    # Fond de l'UI (un simple Panel ou une Entity colorée)
    bg = Entity(parent=camera.ui, model='quad', color=color.black66, scale=(0.5, 0.3), z=1)
    custom_save_ui.append(bg)
    # Texte de titre
    titre = Text(parent=camera.ui, text='Name of world :', position=(0, 0.08), origin=(0, 0), z=0)
    custom_save_ui.append(titre)
    # InputField manuel
    input_field = InputField(parent=camera.ui, position=(0, 0), scale=(0.4, 0.08), limit_alphanumeric=True)
    custom_save_ui.append(input_field)
    # Bouton Valider
    btn_valider = Button(parent=camera.ui, text='Save and quit', position=(0, -0.08), scale=(0.2, 0.06),
                         color=color.azure)
    btn_valider.on_click = lambda: finalize_save()
    custom_save_ui.append(btn_valider)
    # Bouton Annuler
    btn_annuler = Button(parent=camera.ui, text='Cancel', position=(0, -0.16), scale=(0.2, 0.06), color=color.red)
    btn_annuler.on_click = lambda: close_save_ui()
    custom_save_ui.append(btn_annuler)

    print(str(worldexist) + ", " + str(worldpath) + ", " + str(nom_sauvegarde))
def finalize_save():
    global input_field, ss
    main_menu.enabled = False
    main_menu.visible = False
    print("try saving")
    global  worldexist, worldpath, is_saving_now, nom_sauvegarde,epppliatcztdfftdfetg
    if input_field is not None:
        print(input_field.text)
        nom_sauvegarde = input_field.text
    if not os.path.exists("Saves"):
        os.makedirs("Saves")

    # 2. Ouvrir la boite de saisie de texte simple
    print(str(worldexist)+", "+str(worldpath)+", "+str(nom_sauvegarde))
    main_menu.enabled = False
    main_menu.visible = False
    # Si le joueur clique sur Annuler ou ne met rien
    if not nom_sauvegarde:
        print("Sauvegarde annulee '" + str(nom_sauvegarde) + "'")
        main_menu.enabled = True
        return

    # Nettoyage du nom pour enlever les extensions si le joueur les a écrites
    if nom_sauvegarde.endswith(".py"):
        nom_sauvegarde = nom_sauvegarde[:-3]

    filepath = f"Saves/{nom_sauvegarde}.py"
    global selected_slot
    saved_world = {}
    saved_chests = {}
    saved_hoppers = {}
    saved_drops = []

    # 1. Recuperer les entites physiques chargees en 3D
    active_block_positions = set()
    for e in scene.entities:
        # Blocs (Voxel, Chest, Hopper)
        if isinstance(e, (Voxel, Chest, Hopper)):
            pos_tuple = (round(e.x), round(e.y), round(e.z))
            active_block_positions.add(pos_tuple)

            if isinstance(e, Chest):
                saved_chests[str(pos_tuple)] = {
                    "name": getattr(e, 'realname', 'chest'),
                    "data": e.data.copy(),
                    "form": getattr(e, 'type_form', 'cube')
                }
            elif isinstance(e, Hopper):
                saved_hoppers[str(pos_tuple)] = {
                    "name": getattr(e, 'realname', 'hopper'),
                    "data": e.data.copy(),
                    "form": getattr(e, 'type_form', 'cube')
                }

        # Items au sol (FloatingBlock)
        elif e.__class__.__name__ == 'FloatingBlock':
            item_name = getattr(e, 'item_name', 'grass')
            pos_drop = (e.x, e.y, e.z)
            saved_drops.append({
                "name": item_name,
                "position": pos_drop,
                "loaded": True
            })

    # 2. Structurer le world_data global avec l etat loaded pour chaque bloc
    for pos_tuple, block_name in world_data.items():
        is_loaded = pos_tuple in active_block_positions
        saved_world[str(pos_tuple)] = {
            "name": block_name,
            "loaded": is_loaded
        }

    # 3. Sauvegarde de l inventaire du joueur
    saved_inventory = []
    for slot in inventory_slots:
        saved_inventory.append({
            "item_name": slot.item_name,
            "stack": slot.stack,
            "is_empty": slot.is_empty
        })

    # 4. Informations globales du joueur
    player_data = {
        "position": (player.x, player.y, player.z) if player else (0, 10, 0),
        "selected_slot": selected_slot,
        "hp": player_hp
    }

    # 5. Ecriture finale dans le fichier de sauvegarde sans caracteres speciaux
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"world = {repr(saved_world)}\n")
        f.write(f"chests = {repr(saved_chests)}\n")
        f.write(f"hoppers = {repr(saved_hoppers)}\n")
        f.write(f"inventory = {repr(saved_inventory)}\n")
        f.write(f"player_stats = {repr(player_data)}\n")
        f.write(f"dropped_items = {repr(saved_drops)}\n")

    print("Partie sauvegardee avec succes")
    is_saving_now = False
    close_save_ui()
    epppliatcztdfftdfetg.quit()
def close_save_ui():
    global custom_save_ui, main_menu
    for e in custom_save_ui:
        destroy(e)
    main_menu.enabled = True

    main_menu.visible = True
    custom_save_ui = []

def loadGame(file, window, nameoff):
    """
    Charge la partie et instancie les blocs ou items au sol uniquement
    si leur propriete loaded vaut True dans le fichier.
    """
    global world_data, selected_slot, player_hp, worldpath
    import os
    import os
    global main_menu, worldexist, worldpath
    global main_menu, player, crosshair
    # 0. Fermer le menu et activer les contrôles de base
    game_ui.enabled = True
    mouse.locked = True
    mouse.visible = False
    player.enabled = True
    if crosshair:
        crosshair.visible = True
    update_hearts_display()
    update_hotbar()
    # 1. Vérification du fichier avec le bon argument 'file'
    if not os.path.exists(file):
        print("Erreur : Fichier introuvable")
        destroy(window)  # On ferme quand même la fenêtre

        return
    worldpath = nameoff
    # 2. Fermeture de la fenêtre Tkinter
    destroy(window)
    # Nettoyage complet des anciennes entites 3D de la scene
    for e in list(scene.entities):
        if isinstance(e, (Voxel, Chest, Hopper, Sapling)) or e.__class__.__name__ == 'FloatingBlock':
            destroy(e)

    save_vars = {}
    with open(file, "r", encoding="utf-8") as f:
        exec(f.read(), {}, save_vars)

    saved_world = save_vars.get("world", {})
    saved_chests = save_vars.get("chests", {})
    saved_hoppers = save_vars.get("hoppers", {})
    saved_drops = save_vars.get("dropped_items", [])

    world_data.clear()

    # 1. Reconstruction selective du monde selon la propriete loaded
    for pos_str, block_info in saved_world.items():
        pos_tuple = eval(pos_str)
        block_name = block_info["name"]
        is_loaded = block_info.get("loaded", False)

        # On remet le nom brut du bloc dans world_data
        world_data[pos_tuple] = block_name

        # On n instancie en 3D que si loaded est True
        if is_loaded:
            if block_name == "chest":
                c = Chest(position=pos_tuple)
                if pos_str in saved_chests:
                    c.data = saved_chests[pos_str]["data"]
                    c.type_form = saved_chests[pos_str].get("form", "cube")
            elif block_name == "hopper":
                h = Hopper(position=pos_tuple)
                if pos_str in saved_hoppers:
                    h.data = saved_hoppers[pos_str]["data"]
                    h.type_form = saved_hoppers[pos_str].get("form", "cube")
            elif block_name == "sapling":
                Sapling(position=pos_tuple)
            else:
                Voxel(position=pos_tuple, name=block_name)

    # 2. Reconstruction selective des items au sol
    for drop in saved_drops:
        if drop.get("loaded", False):
            if 'FloatingBlock' in globals():
                FloatingBlock(position=drop["position"], name=drop["name"])

    # 3. Restauration de l etat du joueur
    player_stats = save_vars.get("player_stats", {})
    if player_stats and player:
        player.position = player_stats.get("position", (0, 10, 0))
        selected_slot = player_stats.get("selected_slot", 0)
        player_hp = player_stats.get("hp", 20)

    # 4. Restauration graphique de l inventaire
    saved_inventory = save_vars.get("inventory", [])
    for i, slot_data in enumerate(saved_inventory):
        if i < len(inventory_slots):
            slot = inventory_slots[i]
            slot.item_name = slot_data["item_name"]
            slot.stack = slot_data["stack"]
            slot.is_empty = slot_data["is_empty"]

            if not slot.is_empty and slot.item_name != "":
                slot.texture = f"Assets/BaseTextures/{slot.item_name}.png"
                slot.stack_text.text = str(slot.stack) if slot.stack > 1 else ""
            else:
                slot.texture = "Assets/BaseTextures/slot.png"
                slot.stack_text.text = ""

    print("Partie chargee avec succes")
spawn_timer = 0
lasted_tooltip = ""
temps_jeu = 0
vitesse_temps = 0.5
from Bin.drop import shiled_recharging, shiled_time
is_blocking = False
shield_timer = 0.0
cooldown_timer = 0.0
current_sword = "none"

from Bin import config
# Creation du visuel de bouclier au milieu de l ecran
# On la cache au depart (enabled=False)
shield_visual = Entity(
    parent=camera.ui,
    model='quad',
    texture='Assets/BaseTextures/wooden-sword.png', # Texture par defaut
    scale=(0.9, 0.9),
    position=(0, 0),
    rotation=(0, 0, 0), # Inclinee comme une parade de blocage
    enabled=False
)
####################################################
#################### UPDATE ########################
####################################################
def update():
    if not player or not player.enabled:
        return
    #update_chunks()
    ttt()
    global temps_jeu, lumiere_ambiance, filtre_nuit, spawn_timer
    global player_hp, player_max_hp, regen_timer
    global is_blocking, shield_timer, cooldown_timer, shield_visual

    # Gestion de la recharge du bouclier
    if cooldown_timer > 0:
        cooldown_timer -= time.dt

    # Gestion de la fin automatique de la parade
    if is_blocking:
        shield_timer -= time.dt
        if shield_timer <= 0:
            is_blocking = False
            if shield_visual:
                shield_visual.enabled = False
            print("Temps de blocage ecoule")
    # ... Ton code actuel (mouvements, jour/nuit, etc.) ...

    # --- SYSTEME DE REGENERATION AUTOMATIQUE ---
    # On verifie si le joueur est blesse mais toujours vivant
    if 0 < player_hp < player_max_hp:
        regen_timer += time.dt

        # Dès que le chrono atteint le cooldown (4 secondes)
        if regen_timer >= REGEN_COOLDOWN:
            regen_timer = 0  # On reset le chrono

            # On ajoute les PV sans depasser le maximum
            player_hp = min(player_max_hp, player_hp + REGEN_AMOUNT)

            # On met a jour tes images de coeurs (heart0, heart1, heart2)
            if 'update_hearts_display' in globals():
                update_hearts_display()


    else:
        # Si le joueur a toute sa vie, on remet le chrono a zero
        regen_timer = 0
    # On fait avancer le temps du jeu
    temps_jeu += time.dt * vitesse_temps
    global sky
    # On calcule une valeur oscillante entre 0 (nuit) et 1 (jour) avec un sinus
    # (math.sin renvoie entre -1 et 1, donc on adapte la formule)
    luminosite = (math.sin(temps_jeu) + 1) / 2

    # Changement dynamique de la couleur du ciel
    # color.rgb prend (Rouge, Vert, Bleu) entre 0 et 255
    # Ici, le ciel passera d'un bleu clair a un noir complet
    # Au lieu de toucher a mon_ciel.color, on modifie la couleur de la scene
    # La texture reste la, mais elle devient sombre car il n'y a plus de lumiere
    lumiere_ambiance.color = color.rgb(
        int(255 * luminosite),
        int(255 * luminosite),
        int(255 * luminosite)
    )
    filtre_nuit.alpha = (1 - luminosite) * 0.95
    setSizeFrom()
    if held_keys['left mouse']:
        # On fait pivoter la main vers l'avant brusquement
        hand.rotation = Vec3(60, -40, 10)
    else:
        hand.rotation = lerp(hand.rotation, Vec3(30, -20, 0), time.dt * 10)
    is_walking = held_keys['w'] or held_keys['s'] or held_keys['a'] or held_keys['d']
    if is_walking:
        # On utilise le sinus et le cosinus pour faire un mouvement de "huit"
        hand.position = Vec2(0.6, -0.35) + Vec2(
        math.sin(time.time() * 10) * 0.02,
        math.cos(time.time() * 15) * 0.01)
    else:
        # Retour fluide à la position de repos
        hand.position = (0.6, -0.35) # En bas à droite de l'écran
        hand.rotation=(30, -20, 0)
    # --- 2. Animation de Frappe (Retour fluide) ---
    the_void()
    spawn_timer += time.dt
    if spawn_timer >= 10:
        spawn_timer = 0

        # ON VERIFIE SI C'EST LA NUIT
        if is_night():
            Hostile(position=(random.randint(0,20), 5, random.randint(0,20)), name="zombie")
        else:
            Passif(position=(random.randint(0, 20), 5, random.randint(0, 20)), name="cow")
def is_night():
    # On recalcule ou on recupere la luminosite actuelle
    luminosite = (math.sin(temps_jeu) + 1) / 2

    # Si la luminosite est basse, c'est la nuit
    if luminosite < 0.3:
        return True
    else:
        return False
def the_void():
    if player.y <= -40:
        if player.y <= -50:
            player.gravity = 0
            player.jump_height = 0
        if random.random() < 0.5:
            damage_player(4)
from Bin import drop
drops = drop.drops
def ttt():
    selected = inventory_slots[selected_slot]
    global lasted_tooltip
    if selected and not selected.item_name == lasted_tooltip:
        update_item_tooltip()
        lasted_tooltip = selected.item_name
pickaxe_speeds = drop.pickaxe_speeds
required = drop.require
damagex = drop.sword_multipliers
# Cooldown d'attaque du joueur
last_attack_time = 0
ATTACK_COOLDOWN = 0.5  # Temps en secondes entre deux coups (ici 0.5s)
class Voxel(Button):
    def __init__(self, position=(0, 0, 0), name='grass', type_form='cube', blocClass="Voxel", texture_path=""):
        tex_path = f'Assets/BaseTextures/{name.lower()}.png'
        if texture_path:
            tex_path = texture_path
        # Configuration des échelles et des décalages selon la forme choisie
        # Basé sur un bloc standard de 1x1x1 avec origin_y=0.5
        forms = {
            'cube': {'scale': (1, 1, 1), 'offset': (0, 0, 0)},
            'top': {'scale': (1, 0.01, 1), 'offset': (0, 0, 0)},
            'bottom': {'scale': (1, 0.01, 1), 'offset': (0, -0.99, 0)},
            'left': {'scale': (0.01, 1, 1), 'offset': (-0.495, 0, 0)},
            'right': {'scale': (0.01, 1, 1), 'offset': (0.495, 0, 0)},
            'front': {'scale': (1, 1, 0.01), 'offset': (0, 0, 0.495)},
            'back': {'scale': (1, 1, 0.01), 'offset': (0, 0, -0.495)}
        }

        # Sécurité : si la forme demandée n'existe pas, on met un cube par défaut
        selected_form = type_form.lower()
        if selected_form not in forms:
            selected_form = 'cube'

        form_setup = forms[selected_form]

        # Application du décalage à la position d'origine
        final_position = Vec3(position) + Vec3(form_setup['offset'])

        super().__init__(
            parent=scene,
            position=final_position,
            model='cube',
            texture=tex_path,
            origin_y=0.5,
            scale=form_setup['scale'],
            collider='box',
            unlit=True,
            color=color.white
        )

        self.realname = name
        if ifitem(self.realname):
            FloatingBlock(position=self.position, name=self.realname)
            destroy(self)
        self.type_form = selected_form
        self.loaded = False
        # On garde tes variables pour le minage
        self.realname = name
        self.props = block_properties.get(name.lower(), {"breakable": True, "time": 1})
        self.mining_progress = 0

        # On nettoie pour libérer la mémoire

        self.loaded = False

        file_name = self.realname.lower()
        self.BlockData = {
            "Name": self.realname,
            "Class": blocClass,
            "Loaded": self.loaded,
            "BreakProps": self.props,
            "y": self.y,
            "x": self.x,
            "z": self.z,
            "Form": selected_form,
            }

    def update_trader_buttons(self):
        # On nettoie uniquement le contenu défilant
        for c in trader_scroll_area.container.children:
            destroy(c)

        for i, (item, data) in enumerate(trader_offers.items()):
            price, currency = data

            b = Button(
                parent=trader_scroll_area.container,  # On vise le container interne
                text=f"{formatWord(item)}\n({price} {formatWord(currency)})",
                scale=(0.8, 0.2),  # Plus large pour remplir le panneau
                y=-i * 0.25,
                color=color.white,
                texture='Assets/BaseTextures/main-menu.png'
            )
            b.on_click = lambda t=item, p=price, ttt=currency: buy_item(t, p, ttt)

        # On ajuste la limite de scroll selon le nombre d'offres
        trader_scroll_area.max_height = 0.35 + (len(trader_offers) * 0.25)
        # Exemple a mettre a la fin de ta fonction de creation de boutons :
        trader_scroll_area.max_y = 0.4 + (len(trader_offers) * 0.25) - 0.4
    def input(self, key):
        global last_attack_time  # On utilise la variable globale



        if not self.hovered: return
        if self.hovered:

            if self.realname == 'chest':
                # On demande a l objet de s ouvrir/fermer
                if not self.opened:
                    if not player.is_busy:
                        Onmenu_ok()
                        self.open_chest()
                else:
                    self.close_chest()
                    Onmenu_disok()
                return  # On s arrete ici pour ne pas poser de bloc
            if key == 'right mouse down' and self.realname ==  'trader':
                trader_ui.enabled = True
                mouse.locked = False
                mouse.visible = True
                self.update_trader_buttons()
                player.enabled = False
                crosshair.visible = False
                Onmenu_ok()
                return
            elif key == 'right mouse down' and self.realname != 'chest':
                slot = inventory_slots[selected_slot]
                if not slot.is_empty and slot.item_name != "" and slot.item_name.lower() not in item_list:
                    new_pos = self.position + mouse.normal
                    pos_tuple = (round(new_pos.x), round(new_pos.y), round(new_pos.z))
                    world_data[pos_tuple] = slot.item_name
                    # On pose le bloc
                    if slot.item_name == "chest":
                        Chest(position=new_pos)
                    elif slot.item_name == "hopper":
                        Hopper(position=new_pos)
                    elif slot.item_name == "painting":
                        Painting(position=new_pos, face=getface())
                    elif slot.item_name == "sapling":
                        Sapling(position=new_pos)
                    #elif "-flower" in slot.item_name:
                    #    Flower(position=new_pos, color=slot.item_name.replace("-flower", ""))
                    #elif "-carpet" in slot.item_name:
                    #    Carpet(position=new_pos, color=slot.item_name.replace("-carpet", ""))
                    else:
                        Voxel(position=new_pos, name=slot.item_name)
                    # On réduit le stack
                    slot.stack -= 1

                    # Si c'est le dernier bloc, on vide le slot
                    if slot.stack <= 0:
                        slot.item_name = ""
                        slot.texture = 'Assets/BaseTextures/slot.png'  # On remet le skin vide
                        slot.is_empty = True
                        slot.stack = 0

                    # On met à jour le texte du stack
                    if slot.stack > 1:
                        slot.stack_text.text = str(slot.stack)
                    else:
                        slot.stack_text.text = ""


    def update(self):
        # Si on regarde ce bloc et qu'on maintient le clic gauche
        if distance(self, player) < 4:
            if not self.collider:
                self.collider = 'box'
        else:
            if self.collider:
                self.collider = None
        if self.hovered and held_keys['left mouse']:
            if self.props['breakable'] and self.props["time"] > 0:
                # On augmente la progression en fonction du temps défini dans cbdata
                # Si time=3, il faudra 3 secondes pour arriver à 1
                current_item = inventory_slots[selected_slot].item_name.lower()

                # On cherche la vitesse dans le dico, sinon 1.0 (main nue)
                tool_speed = pickaxe_speeds.get(current_item, 1.0)
                self.mining_progress += (time.dt * tool_speed) / self.props['time']
                # On applique la vitesse au temps de base
                # Si le bloc met 3s et qu on a une pioche vitesse 3, ca mettra 1s

                # Effet visuel : le bloc devient de plus en plus rouge/sombre
                self.color = lerp(color.white, color.gray, self.mining_progress)

                if self.mining_progress >= 1:
                    self.break_block()
        else:
            # Si on arrête de miner, le bloc "récupère" doucement
            if self.mining_progress > 0:
                self.mining_progress -= time.dt
                self.color = lerp(color.white, color.gray, self.mining_progress)

    def break_block(self):
        pos_tuple = (round(self.x), round(self.y), round(self.z))
        if pos_tuple in world_data:
            del world_data[pos_tuple]
        voisins = [
            self.position + Vec3(1, 0, 0),  # Droite
            self.position + Vec3(-1, 0, 0),  # Gauche
            self.position + Vec3(0, -1, 0), # Bas
            self.position + Vec3(0, +1, 0), # Haut
            self.position + Vec3(0, 0, 1),  # Devant
            self.position + Vec3(0, 0, -1)  # Derrière
        ]

        for pos in voisins:
            # Utilise round() pour compenser les micro-erreurs de position d'Ursina
            pos_tuple = (round(pos.x), round(pos.y), round(pos.z))

            if pos_tuple in world_data:
                # On vérifie si un bloc physique existe déjà à cette position exacte
                # On cherche parmi toutes les entités de la scène pour éviter les doublons
                existe_deja = False
                for e in scene.entities:
                    if isinstance(e, Voxel) and e.position == pos:
                        existe_deja = True

                        break

                if not existe_deja:
                    new_block = Voxel(position=pos, name=world_data[pos_tuple])
                    new_block.loaded = True
        equipee = inventory_slots[selected_slot].item_name.lower()
        block_name = self.realname.lower()
        peut_ramasser = True

        # Si le bloc a une restriction dans le dictionnaire
        if block_name in required:
            # Si la pioche equipee n est pas dans la liste active
            if equipee not in required[block_name]:
                peut_ramasser = False

        # Si le joueur a le droit de ramasser l item
        if peut_ramasser:
            item_to_drop = block_name
            if item_to_drop in drops:
                item_to_drop = drops[item_to_drop]
            if item_to_drop == 'leaves':
                # Exemple : 25% de chance de donner un sapling, sinon rien ou une pomme
                # Il faudra importer le module random si ce n est pas fait
                import random
                if random.random() < 0.25:
                    item_to_drop = 'sapling'
                else:
                    item_to_drop = 'leaves'
            # L item apparait au sol
            FloatingBlock(position=self.position, name=item_to_drop)


        # Dans tous les cas, le bloc physique dans le monde est detruit
        destroy(self)


import math
from perlin_noise import PerlinNoise

world_data = {}


class Chest(Voxel):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(
            position=position,
            name='chest'
        )
        self.opened = False
        self.inventory_slots = []
        self.data = {}  # Format: {"Nom": Quantite}

    class Slot(Button):
        def __init__(self, slot_index, parent_chest, **kwargs):
            super().__init__(
                parent=camera.ui,
                model='quad',
                color=color.white,
                texture='Assets/BaseTextures/slot.png',
                scale=(0.06, 0.06),
                **kwargs
            )
            self.slot_index = slot_index
            self.parent_chest = parent_chest
            self.item_name = ""
            self.stack = 0

            # On utilise le meme systeme de texte que ton inventaire principal
            self.stack_text = Text(
                parent=self,
                text="",
                scale=27,
                position=(0.2, -0.2, -0.1),
                origin=(0, 0),
                color=color.white,
                add_to_scene_entities=False
            )

        def update_slot(self, name, qty):
            self.item_name = name
            self.stack = qty
            if qty > 0:
                self.texture = f'Assets/BaseTextures/{name}.png'
                self.stack_text.text = str(qty) if qty > 1 else ""
            else:
                self.texture = 'Assets/BaseTextures/slot.png'
                self.stack_text.text = ""

    def refresh_slots(self):
        # On vide l'affichage
        for s in self.inventory_slots:
            s.update_slot("", 0)

        # On remplit avec les donnees
        items_list = list(self.data.items())
        for i in range(len(items_list)):
            if i < len(self.inventory_slots):
                name, qty = items_list[i]
                self.inventory_slots[i].update_slot(name, qty)

    def on_destroy(self):
        for item_name, qty in self.data.items():

            # 2. On fait une boucle sur la quantite
            for i in range(qty):
                # On cree le bloc flottant
                # On ajoute un petit random a la position pour qu ils ne soient pas tous indexes pile au meme endroit
                FloatingBlock(
                    name=item_name,
                    position=self.position + (
                        random.uniform(-0.2, 0.2),
                        0.5,
                        random.uniform(-0.2, 0.2)
                    )
                )

            # Securite : On ferme l interface si elle etait ouverte
        if self.opened:
            self.close_chest()
    def add_item(self, item_name, qty):
        remaining_qty = qty
        # 1. Remplir les stacks existants
        if item_name in self.data:
            space = 64 - self.data[item_name]
            if space > 0:
                add = min(remaining_qty, space)
                self.data[item_name] += add
                remaining_qty -= add

        # 2. Nouveau slot si necessaire
        if remaining_qty > 0 and len(self.data) < 8:
            self.data[item_name] = min(remaining_qty, 64)
            remaining_qty = 0

        if self.opened: self.refresh_slots()
        return remaining_qty == 0

    def open_chest(self):

        if player.is_busy: return
        player.is_busy = True
        self.opened = True
        player.enabled = False
        mouse.visible = True
        mouse.locked = False
        if 'crosshair' in globals(): crosshair.visible = False
        self.props["breakable"] = False
        # Grille 2x4
        for i in range(8):
            s = self.Slot(
                slot_index=i,
                parent_chest=self,
                x=-0.15 + ((i % 4) * 0.1),
                y=0.2 - ((i // 4) * 0.1)
            )
            # Logique pour recuperer un item du coffre
            s.on_click = lambda slot=s: self.take_from_chest(slot)
            self.inventory_slots.append(s)

        self.refresh_slots()

    def take_from_chest(self, slot):
        if slot.stack > 0:
            # On tente d'ajouter a l'inventaire du joueur
            if add_to_inventory(slot.item_name, slot.stack):
                # Si reussi, on le retire du dictionnaire du coffre
                if slot.item_name in self.data:
                    del self.data[slot.item_name]
                self.refresh_slots()

    def close_chest(self):
        self.opened = False
        player.is_busy = False
        player.enabled = True
        mouse.visible = False
        mouse.locked = True
        if 'crosshair' in globals(): crosshair.visible = True
        for s in self.inventory_slots:
            destroy(s)
        self.inventory_slots.clear()
        self.props["breakable"] = True

    def input(self, key):
        # On utilise self.hovered qui est plus stable qu une verification manuelle de l entite
        if self.hovered and mouse.hovered_entity == self:
            if key == 'right mouse down':
                if not self.opened:
                    # Utilise player.is_busy que tu as initialise a la ligne 618
                    if not player.is_busy:
                        self.open_chest()
                        Onmenu_ok()
                else:
                    self.close_chest()
                    Onmenu_disok()

class Hopper(Voxel):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(position=position, name='hopper')
        self.realname = 'hopper'

        # L inventaire interne du hopper (Nom: Quantite)
        self.data = {}

    def update(self):
        # On garde la gestion du collider de ton Voxel original
        super().update()

        # --- LOGIQUE D ASPIRATION (Au-dessus) ---
        # On cherche un FloatingBlock situe 1 case au-dessus du hopper
        try:
            for e in scene.entities:
                if e.__class__.__name__ == 'FloatingBlock':
                    # Si l item flottant est tres proche du dessus du hopper
                    if distance(e.position, self.position + Vec3(0, 1, 0)) < 0.6:
                        self.aspirer_item(e)
            source_pos = self.position + Vec3(0, 1, 0)
            for e in scene.entities:
                # Si c est un coffre ou un autre hopper et qu il est plein
                if (isinstance(e, Chest) or isinstance(e, Hopper)) and e.position == source_pos:
                    # Si le contenant du haut a des items
                    if len(e.data) > 0:
                        # On tente de prendre le premier item disponible
                        item_a_prendre = list(e.data.keys())[0]
                        # On l ajoute a notre propre inventaire (Hopper)
                        if self.add_item(item_a_prendre, 1):
                            # Si reussi, on le retire du contenant du haut
                            e.data[item_a_prendre] -= 1
                            if e.data[item_a_prendre] <= 0:
                                del e.data[item_a_prendre]
                            # On s arrete apres 1 item pour faire un effet de defilement
                            break
        except:
            ""
        finally:
            ""

        # --- LOGIQUE DE TRANSFERT (En-dessous) ---
        # S il y a des items dans le hopper, on essaie de les pousser vers le bas
        if len(self.data) > 0:
            self.pousser_item()

    def aspirer_item(self, floating_block):
        # On recupere le nom de l item au sol
        item_name = floating_block.item_name
        print(f"item {item_name} is aspired")
        # On l ajoute dans l inventaire du hopper
        if item_name in self.data:
            if self.data[item_name] < 64:  # Limite par stack
                self.data[item_name] += 1
                destroy(floating_block)
        else:
            self.data[item_name] = 1
            destroy(floating_block)

    def pousser_item(self):
        # On cherche un coffre place juste en-dessous (y - 1)
        target_pos = self.position + Vec3(0, -1, 0)

        for e in scene.entities:
            if isinstance(e, Chest) and e.position == target_pos:
                # On prend le premier item disponible dans le hopper
                for item_name, qty in list(self.data.items()):
                    # On utilise la fonction add_item de ton coffre !
                    if e.add_item(item_name, 1):
                        # Si le coffre a accepte l item, on le retire du hopper
                        self.data[item_name] -= 1
                        if self.data[item_name] <= 0:
                            del self.data[item_name]

                        return  # On transfere 1 par 1 pour faire un effet de defilement


class Sapling(Voxel):
    def __init__(self, position=(0, 0, 0)):
        # On utilise une texture sapling.png que tu pourras ajouter dans tes Assets
        super().__init__(position=position, name='sapling')
        self.realname = 'sapling'

        # Un sapling ne doit pas bloquer le joueur comme un cube solide
        self.collider = None

        # On definit un temps de pousse aleatoire (ex: entre 10 et 20 secondes)
        # Genere via le module random par exemple, ou une valeur fixe
        self.growth_time = 15.0
        self.age = 0.0

    def update(self):
        # On n appelle pas super().update() pour eviter la logique de collider de distance

        # Le sapling grandit au fil du temps
        self.age += time.dt

        if self.age >= self.growth_time:
            self.grow_into_tree()

    def grow_into_tree(self):
        pos_tuple = (round(self.x), round(self.y), round(self.z))

        # On nettoie world_data avant de detruire le bloc physique
        if pos_tuple in world_data:
            del world_data[pos_tuple]

        # On detruit le sapling physique
        destroy(self)

    def on_destroy(self):
        # IMPORTANT : On doit passer X, Y et Z pour que l arbre apparaisse au bon niveau
        spawn_tree(self.x, self.z)

class Flower(Voxel):
    def __init__(self, position=(0, 0, 0), color="red"):
        name = f"{color.lower()}-flower"
        # Correction ici : super() avec des parenthèses
        super().__init__(position=position, name=name, type_form='bottom')

class Carpet(Voxel):
    def __init__(self, position=(0, 0, 0), color="white"):
        name = f"{color.lower()}-carpet"
        # Correction ici : super() avec des parenthèses
        super().__init__(position=position, name=name, type_form='bottom')
import random
import os
class Painting(Voxel):
    def __init__(self, position=(0, 0, 0), face="front"):
        name_list = os.listdir("Assets/Paints")
        name = f"Assets/Paints/{random.choice(name_list)}"
        super().__init__(position=position, type_form=face, texture_path=name)
def load_structure_from_dict(structure_dict, start_pos=(0, 0, 0)):
    """
    Génère une structure dans le monde à partir d'un dictionnaire de structure.

    :param structure_dict: Le dictionnaire imbriqué {y: {x: {z: block_name}}}
    :param start_pos: Tuple (x, y, z) qui sert de point d'origine (coin inférieur)
    """
    base_x, base_y, base_z = start_pos

    for y_idx, x_dict in structure_dict.items():
        for x_idx, z_dict in x_dict.items():
            for z_idx, block_name in z_dict.items():

                # Si l'emplacement contient un bloc (et n'est pas None)
                if block_name is not None and block_name != "":
                    # On calcule la position réelle dans l'espace Ursina
                    # (On fait -1 si tes index de dictionnaire commencent à 1 pour coller au repère)
                    real_x = base_x + (int(x_idx) - 1)
                    real_y = base_y + (int(y_idx) - 1)
                    real_z = base_z + (int(z_idx) - 1)

                    pos_tuple = (real_x, real_y, real_z)

                    # On l'enregistre dans les données globales du monde
                    world_data[pos_tuple] = block_name

                    # On instancie la classe correspondante selon le type de bloc
                    if block_name == "chest":
                        Chest(position=pos_tuple)
                    elif block_name == "hopper":
                        Hopper(position=pos_tuple)
                    elif block_name == "sapling":
                        Sapling(position=pos_tuple)
                    else:
                        Voxel(position=pos_tuple, name=block_name)

    print("Structure chargée avec succès dans le monde !")


import random
import math
loots_table = drop.loots_table

class Mob(Entity):
    def __init__(self, position=(0, 0, 0), name="mob", max_hp=20, speed=2, **kwargs):
        # Utilisation de .get() pour eviter un KeyError si le nom n existe pas dans le dictionnaire
        if config.entity_models.get(name):
            mdl = f"Assets/Models/{config.entity_models[name]}"
            col = "mesh"
            tex = None
        else:
            mdl = "cube"
            tex = f"Assets/BaseTextures/{name.lower()}.png"
            col = "box"
        super().__init__(
            model=mdl,
            texture=tex,
            position=position,
            scale=(0.9, 1.8, 0.9),  # Taille standard proche d'un joueur/humanoide
            color=color.white,
            collider=col,
            **kwargs
        )
        self.mob_name = name
        self.hp = max_hp
        self.max_hp = max_hp
        self.speed = speed

        # Variables pour l'IA et les déplacements
        self.move_timer = 0
        self.move_direction = Vec3(0, 0, 0)
        self.target_player = None
        self.is_panicking = False
        self.panic_timer = 0

    def update(self):
        # --- 1. GESTION DE LA GRAVITE ET EMPECHEMENT DE COINCEMENT ---
        down_pos = (round(self.x), round(self.y - 1), round(self.z))
        current_pos_feet = (round(self.x), round(self.y), round(self.z))

        is_on_ground = down_pos in world_data

        # ANTI-ETOUFFEMENT : Si le mob est dans un bloc
        if current_pos_feet in world_data:
            self.y += 1.1
            is_on_ground = True

        if not is_on_ground:
            self.y -= 9.8 * time.dt  # Chute libre
        else:
            self.y = round(self.y)

        # --- 2. LOGIQUE DE COMPORTEMENT GLOBAL ---
        if self.is_panicking:
            self.handle_panic()
        else:
            self.handle_ai()

        # --- 3. EXECUTION DU DEPLACEMENT AVEC TOUTES LES DETECTIONS ---
        if self.move_direction != Vec3(0, 0, 0):
            move_step = self.move_direction.normalized() * self.speed * time.dt
            new_pos = self.position + move_step

            # Coordonnees de prediction devant le mob
            check_feet = (round(new_pos.x), round(self.y), round(new_pos.z))
            check_eyes = (round(new_pos.x), round(self.y + 1), round(new_pos.z))
            check_above_head = (round(new_pos.x), round(self.y + 2), round(new_pos.z))

            # --- DETECTION DE CHUTE ET VIDE (MAX 2 BLOCS DÉGATS ACCÈS) ---
            if is_on_ground:
                has_ground_below = False
                # On regarde s'il y a un bloc solide sous ses futurs pieds jusqu'a 3 blocs de profondeur
                for depth in range(1, 4):
                    check_floor = (round(new_pos.x), round(self.y - depth), round(new_pos.z))
                    if check_floor in world_data:
                        has_ground_below = True
                        break  # Un sol securise a ete trouve a une hauteur acceptable

                # Si aucun sol trouve dans la limite de 2 blocs de hauteur (depth 1 et 2)
                # ou que c'est le vide absolu (Skyblock)
                if not has_ground_below:
                    self.move_direction = Vec3(0, 0, 0)  # On stoppe l'avancee
                    self.move_timer = 0  # Force l'IA a recalculer un autre chemin
                    return  # On annule le mouvement

            # --- ANALYSE DE L'OBSTACLE (MONTÉE ET MURS) ---
            # Si un bloc bloque les pieds
            if check_feet in world_data:
                # CAS 1 : Mur de 2 blocs ou plus (les pieds ET les yeux sont bloques)
                if check_eyes in world_data:
                    self.move_direction = Vec3(0, 0, 0)
                    self.move_timer = 0
                    return

                    # CAS 2 : Un seul bloc (les pieds sont bloques mais le reste est libre)
                elif check_above_head not in world_data and is_on_ground:
                    self.y += 1.1  # On saute la marche de 1 bloc
                    self.position += move_step
                else:
                    self.move_direction = Vec3(0, 0, 0)
                    self.move_timer = 0
            else:
                # Si aucun bloc ne bloque les pieds, on avance normalement
                if check_eyes not in world_data:
                    self.position += move_step

            # Orientation visuelle du mob
            self.look_at(self.position + self.move_direction)
            self.rotation_x = 0
            self.rotation_z = 0
    def handle_ai(self):
        """IA de vagabondage par defaut (marche de temps en temps)"""
        self.move_timer -= time.dt
        if self.move_timer <= 0:
            # Choisit une nouvelle direction ou s'arrete (33% de chance de s'arreter)
            if random.random() < 0.33:
                self.move_direction = Vec3(0, 0, 0)
                self.move_timer = random.uniform(1, 3)
            else:
                angle = random.uniform(0, math.pi * 2)
                self.move_direction = Vec3(math.cos(angle), 0, math.sin(angle))
                self.move_timer = random.uniform(2, 5)

    def handle_panic(self):
        """Comportement quand le mob fuit"""
        self.panic_timer -= time.dt
        if self.panic_timer <= 0:
            self.is_panicking = False
            self.speed /= 2  # Reprend sa vitesse normale
            self.move_direction = Vec3(0, 0, 0)
        else:
            # Change de direction de fuite de temps en temps
            if random.random() < 0.05:
                angle = random.uniform(0, math.pi * 2)
                self.move_direction = Vec3(math.cos(angle), 0, math.sin(angle))

    def take_damage(self, amount):
        """Fonction appelee quand le joueur frappe le mob"""
        self.hp -= amount


        # Effet visuel de degats (devient rouge brièvement)
        self.color = color.red
        invoke(setattr, self, 'color', color.white, delay=0.2)
        for i in range(10):
            p_color = color.white
            Particle(position=self.position + Vec3(0, 0.5, 0), color=p_color, texture="damage")
        if self.hp <= 0:
            self.die()

    def die(self):
        for i in range(15):
            p_color = color.white
            Particle(position=self.position + Vec3(0, 0.5, 0), color=p_color)
        dd = random.randint(1, drop.max_orb.get(self.mob_name, 1))
        for i in range(dd):

            XPOrb(position=self.position + Vec3(0, 0.5, 0), xp=drop.xp_loot.get(self.mob_name, 1) / dd)
        item_to_drop = loots_table.get(self.mob_name.lower(), "")
        if 'FloatingBlock' in globals() and item_to_drop:
            FloatingBlock(position=self.position + Vec3(0, 0.5, 0), name=item_to_drop)
        destroy(self)


# ==========================================
# 1. CLASSE DESCENDANTE : MOB PASSIF
# ==========================================
class Passif(Mob):
    def __init__(self, position=(0, 0, 0), name="cow", **kwargs):
        # Un mob passif a generalement moins de vie et va doucement
        super().__init__(position=position, name=name, max_hp=10, speed=1.5, **kwargs)

    def take_damage(self, amount):
        super().take_damage(amount)
        if self.hp > 0 and not self.is_panicking:
            # declenche la panique : court deux fois plus vite pour fuir
            self.is_panicking = True
            self.panic_timer = 4.0
            self.speed *= 2
            angle = random.uniform(0, math.pi * 2)
            self.move_direction = Vec3(math.cos(angle), 0, math.sin(angle))


# ==========================================
# 2. CLASSE DESCENDANTE : MOB NEUTRE
# ==========================================
class Neutral(Mob):
    def __init__(self, position=(0, 0, 0), name="wolf", **kwargs):
        super().__init__(position=position, name=name, max_hp=20, speed=2.0, **kwargs)
        self.is_angry = False

    def handle_ai(self):
        # Si le mob est en colere et que le joueur existe, il le poursuit
        if self.is_angry and player:
            dist = distance(self, player)
            if dist < 15:  # Portee de poursuite
                # Direction vers le joueur
                dir_to_player = (player.position - self.position)
                dir_to_player.y = 0  # Ne cherche pas a s'envoler vers les yeux du joueur
                self.move_direction = dir_to_player.normalized()

                # Si le mob est au corps a corps, il attaque
                if dist < 1.5:
                    self.attack_player()
            else:
                # Le joueur est trop loin, le mob se calme
                self.is_angry = False
                self.speed /= 1.5
                self.move_direction = Vec3(0, 0, 0)
        else:
            # Comportement tranquille par defaut
            super().handle_ai()

    def take_damage(self, amount):
        super().take_damage(amount)
        if self.hp > 0 and not self.is_angry:
            # Devient agressif et augmente sa vitesse de traque
            self.is_angry = True
            self.speed *= 1.5


    def attack_player(self):
        # Systeme d'attaque basique (a adapter avec ton systeme de vie du joueur si tu en as un)
        if random.random() < 0.02:  # Limite le spam d'attaques a chaque frame
            if not is_blocking:
                damage_player(2)


# ==========================================
# 3. CLASSE DESCENDANTE : MOB HOSTILE
# ==========================================
class Hostile(Mob):
    def __init__(self, position=(0, 0, 0), name="zombie", **kwargs):
        # Vitesse de base legerement plus elevee pour traquer le joueur
        super().__init__(position=position, name=name, max_hp=20, speed=2.2, **kwargs)
        self.detection_radius = 12.0  # Distance a laquelle il repere le joueur

    def handle_ai(self):
        if player:
            dist = distance(self, player)
            # Traque automatique si le joueur entre dans son rayon de detection
            if dist <= self.detection_radius:
                dir_to_player = (player.position - self.position)
                dir_to_player.y = 0
                self.move_direction = dir_to_player.normalized()

                if dist < 1.5:
                    self.attack_player()
            else:
                # vagabondage normal si pas de joueur a proximite
                super().handle_ai()
        else:
            super().handle_ai()

    def attack_player(self):
        if random.random() < 0.02:
            if not is_blocking:
                damage_player(3)


class Particle(Entity):
    def __init__(self, position=(0, 0, 0), color=color.white, texture="die", life_time=3, colider=None):
        # On choisit une direction et une vitesse aleatoires pour la projection
        angle = random.uniform(0, math.pi * 2)
        self.velocity = Vec3(
            math.cos(angle) * random.uniform(1, 3),
            random.uniform(2, 5),  # Propulsion vers le haut
            math.sin(angle) * random.uniform(1, 3)
        )

        super().__init__(
            model='cube',
            color=color,
            colider=colider,
            position=position,
            scale=random.uniform(0.1, 0.3),  # Petits éclats
            texture=f"Assets/Particles/{texture}.png"
        )
        self.lifetime = life_time

    def update(self):
        # Diminution du temps de vie restant à chaque frame
        self.lifetime -= time.dt

        # Si le temps est ecoule, on detruit proprement la particule
        if self.lifetime <= 0:
            destroy(self)
            return  # On arrete l'update ici

        # Physique de la particule
        self.velocity.y -= 9.8 * time.dt
        self.position += self.velocity * time.dt

        # On garde le retrecissement visuel pour l'effet de disparition progressif
        self.scale -= 0.3 * time.dt


class XPOrb(Particle):
    def __init__(self, xp=1, position=(0, 0, 0)):
        self.xp = float(xp)
        paliers_xp = [
            (15, "small_orb"),
            (50, "orb"),
            (100, "big_orb")
        ]
        tex = next((texture for plafond, texture in paliers_xp if self.xp <= plafond), "big_orb")

        super().__init__(
            texture=tex,
            position=position,
            colider="box",
        )

    def update(self):
        # Si ignore est True ou si l entite n a plus de position, on stoppe immediatement
        # --- LOGIQUE DE GRAVITE ET COLLISION SEULE (SANS RETRECISSEMENT) ---
        # Initialisation de la vitesse si elle n existe pas
        if not hasattr(self, "velocity"):
            from ursina import Vec3
            self.velocity = Vec3(0, 0, 0)

        # 1. Application de la gravite sur la vitesse verticale
        self.velocity.y -= 9.8 * time.dt

        # 2. Deplacement de l entite
        self.position += self.velocity * time.dt

        # 3. Detection du sol via world_data
        bx = round(self.x)
        by = round(self.y - 0.1)  # On teste le bloc juste en dessous de l orbe
        bz = round(self.z)

        if (bx, by, bz) in world_data:
            # Si un bloc est trouve, on stoppe la chute et on cale l orbe pile dessus
            self.y = by + 1.0
            self.velocity.y = 0
    def collect(self):
        global player
        if not self.ignore:
            # On passe ignore a True pour que l update s arrete net au debut
            self.ignore = True

            # Application de l XP au joueur
            player.xp += self.xp
            print("xp gagner xp = " + str(player.xp))

            # On desactive les collisions pour eviter un double declenchement
            self.collider = None

            # Au lieu de destroy(self) direct, on decale la destruction a la frame suivante
            invoke(destroy, self, delay=0.01)
shop_structure = {
        1: {  # Couche sol
            1: {1: "plank", 2: "plank", 3: "plank"},
            2: {1: "plank", 2: "plank", 3: "plank"},
            3: {1: "plank", 2: "plank", 3: "plank"},
        },
        2: {  # Murs et Trader
            1: {1: "plank", 2: None, 3: "plank"},
            2: {1: None, 2: "trader", 3: None},
            3: {1: "plank", 2: None, 3: "plank"},
        },
        3: {  # Murs et Déco
            1: {1: "plank", 2: None, 3: "plank"},
            2: {1: None, 2: "hay-bale", 3: None},
            3: {1: "plank", 2: None, 3: "plank"},
        },
        4: {  # Toit
            1: {1: "wool", 2: "wool", 3: "wool"},
            2: {1: "wool", 2: "wool", 3: "wool"},
            3: {1: "wool", 2: "wool", 3: "wool"},
        }
    }
from Bin import trades
trader_offers = trades.trader_offers



def spawn_shop(start_x, start_z):
    # 1. On trouve la hauteur du sol pour poser la structure
    ground_y = 0
    for y_check in range(15, -10, -1):
        if (start_x, y_check, start_z) in world_data:
            ground_y = y_check
            break

    # 2. NETTOYAGE DE LA ZONE (3x4x3)
    # On définit la zone à vider (un peu plus large pour être sûr)
    for dy in range(1, 6):  # On nettoie sur 5 blocs de haut
        for dz in range(1, 4):  # Zone 3x3
            for dx in range(1, 4):
                target_pos = (start_x + dx, ground_y + dy, start_z + dz)

                # On retire des données
                if target_pos in world_data:
                    del world_data[target_pos]

                # On détruit l'entité physique si elle existe déjà
                for e in scene.entities:
                    try:
                        if not e : pass
                        if isinstance(e, Voxel) and e.position == target_pos:
                            destroy(e)
                    except:
                        ""
                    finally:
                        ""

    # 3. APPARITION DE LA STRUCTURE (Ton schéma)
    for dy, layers in shop_structure.items():
        for dz, rows in layers.items():
            for dx, block_name in rows.items():
                if block_name is not None:
                    pos = (start_x + dx, ground_y + dy, start_z + dz)

                    # On enregistre et on fait apparaître
                    world_data[pos] = block_name
                    Voxel(position=pos, name=block_name)
def spawn_tree(x, z):
    # 1. On trouve la hauteur du sol à cet endroit
    if (x, 0, z) in world_data:
        ground_y = 0
        # On cherche le bloc le plus haut pour poser l'arbre dessus
        for y_check in range(10, -10, -1):
            if (x, y_check, z) in world_data:
                ground_y = y_check
                break

        # 2. On crée le tronc (3 blocs de haut)
        trunk_height = 3
        for i in range(1, trunk_height + 1):
            world_data[(x, ground_y + i, z)] = 'wood'
            # On le fait apparaître physiquement tout de suite
            Voxel(position=(x, ground_y + i, z), name='wood')


        # 3. On crée les feuilles (une petite croix au sommet)
        leaf_y = ground_y + trunk_height + 1
        leaf_positions = [
            (x, leaf_y, z),  # Sommet
            (x + 1, leaf_y - 1, z), (x - 1, leaf_y - 1, z),  # Côtés
            (x, leaf_y - 1, z + 1), (x, leaf_y - 1, z - 1)  # Devant/Derrière
        ]

        for l_pos in leaf_positions:
            world_data[l_pos] = 'leaves'
            Voxel(position=l_pos, name='leaves')


def generate_optimized_world(worldXZSize, seed):
    # On définit les bruits UNE SEULE FOIS au début
    if not seed or seed == 0: return
    print("World seed : " + str(seed))
    noise = PerlinNoise(octaves=2, seed=seed)
    tree_noise = PerlinNoise(octaves=5, seed=seed)
    ore_noise = PerlinNoise(octaves=10, seed=seed)

    couche_fond = -20

    # 1. GÉNÉRATION DES DONNÉES (Le dictionnaire)
    for x in range(worldXZSize):
        for z in range(worldXZSize):
            # Hauteur de la surface
            y_max = math.floor(noise([x / 24, z / 24]) * 6)

            for y in range(couche_fond, y_max + 1):
                # Bruit 3D pour les minerais
                # Calcul du bruit 3D
                ore_val = ore_noise([x / 8, y / 8, z / 8])  # On réduit le diviseur pour des filons plus gros

                if y == y_max:
                    name = 'grass'
                elif y > y_max - 3:
                    # Fossiles : plus fréquents (on baisse de 0.4 à 0.25)
                    name = 'dirt-fossil' if ore_val > 0.25 else 'dirt'
                elif y == couche_fond:
                    name = 'obsidite'
                elif y > y_max - 12:
                    # Pierre avec Fer et Or
                    if ore_val > 0.3:  # Fer (Seuil baissé)
                        name = 'iron-ore'
                    elif ore_val < -0.35:  # Or (On utilise les valeurs négatives du bruit !)
                        name = 'golden-ore'
                    else:
                        name = 'stone'

                else:
                    # Profondeur avec Diamants et Fissures
                    if ore_val > 0.35:  # Diamant
                        name = 'diamond-ore'
                    elif ore_val > 0.25:  # Petrole (entre 0.1 et 0.35)
                        name = 'oil-block'
                    elif ore_val < -0.3:  # Fissure
                        name = 'fisere-ore'
                    else:
                        name = 'old-stone'

                world_data[(x, y, z)] = name

    # 2. AFFICHAGE PHYSIQUE (Seulement ce qui est visible)
    for x in range(worldXZSize):
        for z in range(worldXZSize):
            for y_surf in range(15, couche_fond - 1, -1):
                if (x, y_surf, z) in world_data:
                    Voxel(position=(x, y_surf, z), name=world_data[(x, y_surf, z)])
                    break  # On ne crée que le bloc du dessus pour éviter le lag
    # À la fin de generate_optimized_world
    spawn_shop(10, 10)  # Fait apparaître un shop aux coordonnées 10, 10
    # 3. GÉNÉRATION DES ARBRES (Forêts par zones)
    for x in range(2, worldXZSize - 2):
        for z in range(2, worldXZSize - 2):
            # Le bruit de l'arbre définit si on est dans un biome "Forêt"
            if tree_noise([x / 8, z / 8]) > 0.2:
                for y_surf in range(12, -5, -1):
                    if (x, y_surf, z) in world_data and world_data[(x, y_surf, z)] == 'grass':
                        if random.random() > 0.92:  # Ajuste pour la densité
                            spawn_tree(x, z)
                        break
    def flowerspwn():
        for x in range(worldXZSize):
            for z in range(worldXZSize):
                # On définit une chance globale d'avoir une fleur sur cette case (ex: 7% de chance)
                if random.random() < 0.07:
                    for y_surf in range(15, couche_fond - 1, -1):
                        # On cherche le bloc de grass en surface
                        if (x, y_surf, z) in world_data and world_data[(x, y_surf, z)] == 'grass':
                            # On vérifie que la place juste au-dessus est libre (pas d'arbre ni de shop)
                            if (x, y_surf + 1, z) not in world_data:

                                # Choix de la couleur avec la structure réclamée
                                flower_val = random.random()
                                if flower_val < 0.2:
                                    chosen_color = 'yellow'
                                elif flower_val < 0.4:
                                    chosen_color = 'red'
                                elif flower_val < 0.6:
                                    chosen_color = 'green'
                                elif flower_val < 0.8:
                                    chosen_color = 'blue'
                                else:
                                    chosen_color = 'pink'

                                flower_name = f"{chosen_color}-flower"
                                flower_pos = (x, y_surf + 1, z)

                                # On l'enregistre dans les données du monde et on l'instancie
                                world_data[flower_pos] = flower_name
                                Voxel(position=flower_pos, name=flower_name)
                            break
    flowerspwn()
# On crée une classe spéciale pour les blocs animés
class FloatingBlock(Entity):
    def __init__(self, position=(0, 0, 0), name='grass'):
        # On détermine le scale avant le super().__init__
        # Si c'est un item (plat), on met 0.1, sinon 0.4 (cube)
        # On peut même affiner pour que l'item soit très plat sur un axe
        current_scale = 0.4
        if ifitem(name):
            current_scale = (0.4, 0.4, 0.0001) # Format "carte/item" plat
        else:
            current_scale = 0.4 # Format "petit bloc"

        super().__init__(
            model='cube',
            position=position,
            texture=f'Assets/BaseTextures/{name.lower()}.png',
            scale=current_scale,
            collider='box'
        )
        self.apparence = f'Assets/BaseTextures/{name.lower()}.png'
        self.start_y = position[1]
        self.item_name = name.lower()
        self.t = random.uniform(0, 5)  # Pour que tous les blocs ne montent pas en même temps

    def update(self):
        # --- LOGIQUE DE GRAVITE ET COLLISION SEULE (SANS RETRECISSEMENT) ---
        # Initialisation de la vitesse si elle n existe pas
        if not hasattr(self, "velocity"):
            from ursina import Vec3
            self.velocity = Vec3(0, 0, 0)

        # 1. Application de la gravite sur la vitesse verticale
        self.velocity.y -= 9.8 * time.dt

        # 2. Deplacement de l entite
        self.position += self.velocity * time.dt

        # 3. Detection du sol via world_data
        bx = round(self.x)
        by = round(self.y - 0.1)  # On teste le bloc juste en dessous de l orbe
        bz = round(self.z)

        if (bx, by, bz) in world_data:
            # Si un bloc est trouve, on stoppe la chute et on cale l orbe pile dessus
            self.y = by + 1.0
            self.velocity.y = 0
        self.rotation_y += 50 * time.dt
        self.t += time.dt
        self.y = self.start_y + math.sin(self.t * 3) * 0.2

        # --- 3. Détection du ramassage ---
        if player and distance(self, player) < 1.5:
            self.collect()

    def collect(self):
        global inventory_slots
        found = False

        # 1. On cherche si l'item existe déjà pour l'empiler
        for slot in inventory_slots:
            if slot.item_name == self.item_name and slot.stack < 64:  # Limite de 64
                slot.stack += 1
                found = True
                break

        # 2. Si pas trouvé, on cherche un slot vide
        if not found:
            for slot in inventory_slots:
                if slot.is_empty:
                    slot.item_name = self.item_name
                    slot.texture = self.apparence
                    slot.is_empty = False
                    slot.stack = 1
                    found = True
                    break

        # Mise à jour de l'affichage des textes
        self.update_inventory_ui()

        if found:
            destroy(self)

    def update_inventory_ui(self):
        for slot in inventory_slots:
            if slot.stack > 1:
                slot.stack_text.text = str(slot.stack)
            else:
                slot.stack_text.text = ""  # On cache le "1" pour que ce soit plus joli

# --- EXEMPLE D'UTILISATION ---
# Tu peux l'ajouter dans ton main() pour tester
# item = FloatingBlock(position=(5, 1, 5), texture='Assets/BaseTextures/grass.png')

####################################################
#################### INPUT #########################
####################################################
def input(key):
    global main_menu, player, title_text, play_button, game_ui, selected_slot, last_attack_time
    global crafting_ui, craft_input_1, craft_input_2, craft_output, chat_input, chat_display, _on_menu_
    if key == 'escape':
        # On vérifie si le menu est actuellement affiché ou non
        if main_menu.enabled:
            resume_game()
            Onmenu_disok()
        else:
            Onmenu_ok()
            pause_game() # On appelle une fonction pause qu'on va créer
    if key == 't':
        # CAS 1 : Le chat est ferme, on l'ouvre
        if not chat_input.enabled:
            Onmenu_ok()
            chat_input.enabled = True
            chat_input.active = True  # Met le focus sur le texte
            player.cursor.enabled = True  # Affiche la souris si besoin
            player.speed = 0  # On empeche le joueur de bouger pendant qu'il ecrit
            player.jump_height = 0

        # CAS 2 : Le chat est ouvert, on valide et envoie le message
        else:
            message = chat_input.text.strip()
            Onmenu_disok()
            if message:  # Si le message n'est pas vide

                # On l'ajoute au chat en tant que "Joueur"

                # --- BONUS : SYSTEME DE COMMANDES ---
                # Si le joueur tape "/heal", ca lui redonne toute sa vie
                if message == "/heal":
                    global player_hp, player_max_hp
                    player_hp = player_max_hp
                    return

                add_chat_message(message, sender=pseudo_joueur)

            # On vide le champ et on cache le chat
            chat_input.text = ''
            chat_input.enabled = False
            chat_input.active = False
            player.cursor.enabled = False
            player.speed = 8  # On redonne ses mouvements de base au joueur
            player.jump_height = 0.75  # Remplace par ta valeur habituelle
    if key == 'e':
        if not _on_menu_:
            crafting_ui.enabled = not crafting_ui.enabled
            mouse.locked = not crafting_ui.enabled
            mouse.visible = crafting_ui.enabled
            player.enabled = not crafting_ui.enabled
            if not crafting_ui.enabled:
                exitCraftsys()
    # Sélection de la hotbar (1-9)
    if key in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
        if not _on_menu_:
            selected_slot = int(key) - 1
            update_hotbar()
            update_item_tooltip()
    global is_blocking, shield_timer, cooldown_timer, current_sword, shield_visual

    if key == 'right mouse down':
        # On recupere l item actuel depuis les slots d inventaire
        current_item = inventory_slots[selected_slot].item_name

        # On verifie si cet item est une epee connue dans notre dictionnaire
        if current_item in shiled_time and cooldown_timer <= 0 and not is_blocking:
            is_blocking = True
            current_sword = current_item
            shield_timer = shiled_time[current_sword]
            cooldown_timer = shiled_recharging[current_sword]

            # On applique la texture correspondante a l epee tenue et on l affiche
            if shield_visual:
                shield_visual.texture = "Assets/BaseTextures/" + str(current_sword) + ".png"
                shield_visual.enabled = True

            print("Parade commencee avec " + str(current_sword))

    # Si le joueur relache le clic droit avant la fin du temps, on enleve le bouclier
    if key == 'right mouse up':
        if is_blocking:
            is_blocking = False
            if shield_visual:
                shield_visual.enabled = False
            print("Parade arretee par le joueur")
    if key == 'left mouse down':
        current_time = time.time()

        # 1. Si on clique directement sur le collider du Mob
        if mouse.hovered_entity and isinstance(mouse.hovered_entity, Mob):
            if distance(player, mouse.hovered_entity) < 4:
                if current_time - last_attack_time >= ATTACK_COOLDOWN:
                    mouse.hovered_entity.take_damage(5)
                    last_attack_time = current_time
                return

        # 2. Si le Mob est sur le bloc (on utilise mouse.world_point a la place de hit_point)
        hit_mob = None
        if mouse.world_point:
            target_pos = mouse.world_point
        else:
            if player is not None:
                target_pos = player.position

        for entity in scene.entities:
            if isinstance(entity, Mob) and distance(entity, target_pos) < 1.5:
                hit_mob = entity
                break
        current_item = inventory_slots[selected_slot].item_name.lower()

        # On cherche la vitesse dans le dico, sinon 1.0 (main nue)
        tool_speed = damagex.get(current_item, 1.0)
        if hit_mob and distance(player, hit_mob) < 4:
            if current_time - last_attack_time >= ATTACK_COOLDOWN:
                hit_mob.take_damage(2 * tool_speed)
                last_attack_time = current_time
            return



def update_hotbar():
    # Met à jour l'apparence visuelle de la sélection
    for i, slot in enumerate(inventory_slots):
        slot.color = color.azure if i == selected_slot else color.white
def resume_game():
    global main_menu, player, game_ui
    if main_menu:
        main_menu.enabled = False
        game_ui.enabled = True # On affiche l'UI du jeu
        mouse.locked = True
        mouse.visible = False
        player.enabled = True
def pause_game():
    global main_menu, player, game_ui, title_text, play_button, arriereplan
    main_menu.enabled = True
    game_ui.enabled = False
    play_button.on_click = resume_game
    title_text.text = 'Game settings' # On change le titre
    play_button.text = 'To resume'        # On change le texte du bouton
    mouse.locked = False
    mouse.visible = True
    player.enabled = False


def add_to_inventory(name, amount):
    """Ajoute des objets en gérant le surplus (ex: si amount = 128)"""
    global inventory_slots

    # Tant qu'il reste des items à donner
    while amount > 0:
        found_slot = False

        # 1. On cherche d'abord à remplir des stacks existants de cet item
        for slot in inventory_slots:
            if not slot.is_empty and slot.item_name == name and slot.stack < 64:
                add_qty = min(amount, 64 - slot.stack)  # On prend ce qu'on peut ajouter
                slot.stack += add_qty
                amount -= add_qty
                slot.stack_text.text = str(slot.stack)
                found_slot = True
                if amount <= 0: return True  # On a tout distribué
                break  # On sort du for pour rescanner avec le nouvel amount

        # 2. Si on n'a pas pu tout mettre dans des stacks existants, on cherche un slot vide
        if not found_slot:
            for slot in inventory_slots:
                if slot.is_empty:
                    slot.item_name = name
                    slot.texture = f'Assets/BaseTextures/{name}.png'
                    add_qty = min(amount, 64)  # On remplit au max à 64
                    slot.stack = add_qty
                    amount -= add_qty
                    slot.is_empty = False
                    slot.stack_text.text = str(slot.stack) if slot.stack > 1 else ""
                    found_slot = True
                    if amount <= 0: return True
                    break

        # 3. Si on n'a trouvé ni stack à remplir, ni slot vide, l'inventaire est plein
        if not found_slot:

            return False

    return True

def check_craft():
    global craft_input_1, craft_input_2, craft_output

    # On récupère le contenu précis de chaque slot
    # Si le slot est vide, on met (None, 0)
    s1_name = craft_input_1.item_name if not craft_input_1.is_empty else None
    s1_qty = craft_input_1.stack if not craft_input_1.is_empty else 0

    s2_name = craft_input_2.item_name if not craft_input_2.is_empty else None
    s2_qty = craft_input_2.stack if not craft_input_2.is_empty else 0

    # On crée la signature de ce qu'il y a sur la table
    current_table = ((s1_name, s1_qty), (s2_name, s2_qty))

    # On compare avec le dictionnaire
    if current_table in recipes:
        res_name, res_qty = recipes[current_table]
        craft_output.item_name = res_name
        craft_output.texture = f'Assets/BaseTextures/{res_name}.png'
        craft_output.stack = res_qty
        craft_output.is_empty = False
        craft_output.color = color.white
        craft_output.stack_text.text = str(res_qty) if res_qty > 1 else ""
    else:
        # Pas de recette correspondante
        clear_slot(craft_output)
        craft_output.color = color.white


def transfer_item(from_slot, to_slot):
    if not from_slot.is_empty:
        # 1. Verification : slot vide OU meme item ET pas depassement de 64
        if to_slot.is_empty or to_slot.item_name == from_slot.item_name:
            if to_slot.stack < 64:
                to_slot.item_name = from_slot.item_name
                to_slot.texture = from_slot.texture
                to_slot.is_empty = False

                # On transfere l unite
                to_slot.stack += 1
                from_slot.stack -= 1

                # 2. Mise a jour du texte de l'inventaire
                if from_slot.stack <= 0:
                    clear_slot(from_slot)
                else:
                    from_slot.stack_text.text = str(from_slot.stack) if from_slot.stack > 1 else ""

                # 3. Mise a jour du texte du slot de craft
                # On force la mise a jour du texte pour voir que le nombre augmente
                if hasattr(to_slot, 'stack_text'):
                    to_slot.stack_text.text = str(to_slot.stack) if to_slot.stack > 1 else ""

                # On relance le check des recettes de craft
                check_craft()

def clear_slot(slot):
    """Réinitialise complètement un slot"""
    slot.is_empty = True
    slot.item_name = ""
    slot.texture = 'Assets/BaseTextures/slot.png'
    slot.stack = 0
    if hasattr(slot, 'stack_text'):
        slot.stack_text.text = ""


def item_click(slot):
    # 1. Gestion du Crafting
    if crafting_ui.enabled and not slot.is_empty:
        # ETAPE A : On cherche d'abord un slot vide pour l'occuper
        if craft_input_1.is_empty:
            transfer_item(slot, craft_input_1)
        elif craft_input_2.is_empty:
            transfer_item(slot, craft_input_2)

        # ETAPE B : Si les deux sont pleins, on tente le stack (remplir jusqu'a 64)
        elif craft_input_1.item_name == slot.item_name and craft_input_1.stack < 64:
            transfer_item(slot, craft_input_1)
        elif craft_input_2.item_name == slot.item_name and craft_input_2.stack < 64:
            transfer_item(slot, craft_input_2)

        check_craft()
        return

    # 2. Gestion du Coffre (ton code existant)
    for e in scene.entities:
        if isinstance(e, Chest) and e.opened:
            if e.add_item(slot.item_name, slot.stack):
                clear_slot(slot)
            return

def buy_item(item_name, cost, currency):
    # 1. On vérifie si le joueur a assez de monnaie
    total_currency = 0
    for slot in inventory_slots:
        if slot.item_name == currency:
            total_currency += slot.stack

    if total_currency >= cost:
        # 2. On retire le prix de l'inventaire
        remaining_to_pay = cost
        for slot in inventory_slots:
            if slot.item_name == currency:
                take = min(slot.stack, remaining_to_pay)
                slot.stack -= take
                remaining_to_pay -= take
                if slot.stack <= 0:
                    clear_slot(slot)
                else:
                    slot.stack_text.text = str(slot.stack)
                if remaining_to_pay <= 0: break

        # 3. On donne l'objet acheté
        add_to_inventory(item_name, 1)
hearts_sprites = []

def setup_hearts_ui():
    global hearts_sprites

    # On commence a gauche et on decale chaque coeur vers la droite
    start_x = -0.25
    spacing = 0.045  # Espace entre chaque coeur a l'ecran

    for i in range(10):
        # On cree une entite 2D attachee a la camera
        heart_sprite = Entity(
            parent=game_ui,
            model='quad',
            texture='Assets/BaseTextures/heart2.png',  # Texture par defaut au depart
            scale=(0.04, 0.04),  # Taille du sprite a l'ecran
            position=(start_x + (i * spacing), -0.4),  # Alignement horizontal
            origin=(0, 0)
        )
        hearts_sprites.append(heart_sprite)

def update_hearts_display():
    global player_hp, hearts_sprites

    # On s'assure que la vie reste dans les limites autorisees (0 a 20)
    current_hp = max(0, min(player_hp, 20))

    for i in range(10):
        # Chaque index i represente le coeur qui gere les points (i*2 + 1) et (i*2 + 2)
        # Exemple pour le coeur index 0 : il check les PV 1 et 2
        heart_value = i * 2

        # CAS 1 : Le joueur a les deux points de PV pour ce coeur
        if current_hp >= heart_value + 2:
            hearts_sprites[i].texture = 'Assets/BaseTextures/heart2.png'  # Coeur complet

        # CAS 2 : Il ne reste qu'un seul point (le coeur est coupe en deux)
        elif current_hp == heart_value + 1:
            hearts_sprites[i].texture = 'Assets/BaseTextures/heart1.png'  # Demi coeur

        # CAS 3 : Les PV sont en dessous de la valeur de ce coeur
        else:
            hearts_sprites[i].texture = 'Assets/BaseTextures/heart0.png'  # Coeur vide
import inspect
def damage_player(amount):
    global player_hp, last_player_damaged_time, player

    current_time = time.time()
    # On verifie si le joueur est encore sous le coup de l'immunite temporaire
    if current_time - last_player_damaged_time >= PLAYER_DAMAGED_COOLDOWN:
        player_hp -= amount
        last_player_damaged_time = current_time

        cadre = inspect.currentframe().f_back
        infos = inspect.getframeinfo(cadre)
        nom_appeleur = infos.function  # Contient le nom de la fonction (ex: 'attack_player')

        # On essaie de recuperer le nom de la classe de l'attaquant (ex: Zombie, Wolf)
        # 'self' est generalement present dans les arguments de la fonction d'une classe
        tueur = "Unknown"
        if 'self' in cadre.f_locals:
            instance = cadre.f_locals['self']
            # On recupere le nom du mob (comme 'cow', 'zombie', etc.) s'il existe
            if hasattr(instance, 'mob_name'):
                tueur = instance.mob_name
            else:
                tueur = instance.__class__.__name__
        else:
            # Si ce n'est pas une classe, on prend le nom de la fonction (ex: lave, chute...)
            tueur = nom_appeleur
        # Effet visuel optionnel : un flash rouge rapide sur l'ecran (si tu as une camera/UI)
        # Ou tu peux faire reculer un peu le joueur (knockback)
        for i in range(15):
            p_color = color.white
            Particle(position=player.position + Vec3(0, 0.5, 0), color=p_color, texture="damage")
        update_hearts_display()
        if player_hp <= 0:
            player_die(killer_name=tueur)


def player_die(killer_name="NULL"):
    global player_hp, player

    # Ici, tu as deux choix pour la mort :

    # Choix A : Le TP au spawn et reset de la vie (Style Minecraft)
    player_hp = player_max_hp
    for i in range(15):
        p_color = color.white
        Particle(position=player.position + Vec3(0, 0.5, 0), color=p_color)

    formatted = killer_name.replace("-", " ").replace("_", " ").capitalize()
    add_chat_message(f"{pseudo_joueur} was killed by {formatted}")
    def tp():

        player.gravity = 1
        player.jump_height = 0.75
        player.x = random.randint(1, 20)
        player.z = random.randint(1, 20)
        # Variables cibles (par exemple choisies au hasard)
        cible_x = player.x
        cible_z = player.z

        hauteur_max = 0  # Valeur par defaut si aucun bloc n est trouve

        # On parcourt toutes les positions existantes dans le dictionnaire du monde
        for (bx, by, bz) in world_data.keys():
            if bx == cible_x and bz == cible_z:
                if by > hauteur_max:
                    hauteur_max = by
        player.y = hauteur_max + 1
        # Ici, hauteur_max contient le Y le plus haut pour cette colonne

        update_hearts_display()
    invoke(tp, delay=1)


# --- SYSTEME DE CHAT GLOBAL ---
chat_messages = []
max_chat_lines = 8  # Nombre maximum de messages affiches en meme temps

# Zone de texte Ursina pour afficher le chat en bas a gauche de l'ecran



def add_chat_message(text, sender=""):
    """Ajoute un message dans le chat et actualise l'affichage"""
    global chat_messages
    if sender:
        formatted_text = f"{text} ({sender})"
    else:
        formatted_text = f"{text}"
    # Formatage du message (Pas de caracteres speciaux)

    chat_messages.append(formatted_text)

    # Si on depasse la limite, on supprime le plus vieux message
    if len(chat_messages) > max_chat_lines:
        chat_messages.pop(0)

    # On reconstruit le texte de la boite en sautant des lignes
    chat_display.text = '\n'.join(chat_messages)

def exitCraftsys():
    global craft_output, craft_input_1, craft_input_2

    # Liste des slots a vider
    slots_to_clear = [craft_input_1, craft_input_2]

    for slot in slots_to_clear:
        if slot and not slot.is_empty:
            # On tente d ajouter a l inventaire
            # On passe le nom de l item et sa quantite (stack)
            success = add_to_inventory(slot.item_name, slot.stack)

            # Si l inventaire est plein, on fait spawn l item au sol
            if not success:
                for i in range(slot.stack):
                    FloatingBlock(
                        name=slot.item_name,
                        position=player.position + (0, 1, 0)
                    )

            # On nettoie le slot apres avoir rendu les items
            clear_slot(slot)
    clear_slot(craft_output)
import time
ttxxtt = None
loading_screen = None
def main():
    give = add_to_inventory
    global ttxxtt
    global crafting_ui, craft_input_1, craft_input_2, craft_output, chat_input, chat_display, sky, lumiere_ambiance, hearts_ui
    global player, main_menu, title_text, play_button, game_ui, inventory_slots, hand, arriereplan, crosshair, filtre_nuit
    app = Ursina(
        title="Cubica - Adventure Awaits",
        borderless=False,
        show_ursina_splash=True,
        editor_ui_enabled=False,
    )
    scene.fog_density = 0.05  # Cache la fin du monde proprement
    # Configuration des polices
    Text.default_font = 'Assets/Fonts/Minecraft.ttf'
    #eastereggin 88203967
    sky = Sky(color=color.white)
    filtre_nuit = Sky()
    filtre_nuit.texture = None  # Pas de texture, juste une couleur unie
    filtre_nuit.color = color.black
    filtre_nuit.alpha = 0
    global epppliatcztdfftdfetg
    #ground = Entity(model='plane', texture='white', scale=100, collider='box', color=color.green)
    #seed = random.randint(0, 99999999)
    #seed = 88203967
    #generate_optimized_world(20, seed)

    # Tableau global pour stocker les 10 images des coeurs

        # --- JOUEUR ---

    # --- JOUEUR ---
      # Le joueur n est pas occupe au depart

    # --- INTERFACE DE JEU (HUD) ---
    game_ui = Entity(parent=camera.ui, enabled=False)
    crafting_ui = Entity(parent=camera.ui, enabled=False)

    # On crée 2 slots d'entrée et 1 slot de sortie
    craft_input_1 = Button(parent=crafting_ui, scale=0.06, position=(-0.1, 0.1), texture='Assets/BaseTextures/slot.png', color=color.white)
    craft_input_2 = Button(parent=crafting_ui, scale=0.06, position=(0, 0.1), texture='Assets/BaseTextures/slot.png', color=color.white)
    craft_output = Button(parent=crafting_ui, scale=0.06, position=(0.15, 0.1), texture='Assets/BaseTextures/slot.png',
                          color=color.white)
    craft_input_1.is_empty = True
    craft_input_1.stack = 0
    craft_input_1.item_name = ""
    craft_input_2.is_empty = True
    craft_input_2.stack = 0
    craft_input_2.item_name = ""
    craft_output.is_empty = True
    craft_output.item_name = ""
    craft_output.stack = 0
    craft_input_1.stack_text = Text(
        parent=craft_input_1,
        text="",
        scale=27,  # Augmente si c'est trop petit (Ursina scale est relatif au parent)
        position=(0.2, -0.2, -0.1),  # Le Z à -0.1 le met DEVANT le bouton
        origin=(0, 0),
        color=color.white,
        # On s'assure que le texte ne bouge pas
        add_to_scene_entities=False
    )
    chat_display = Text(
        text='',
        position=(-0.85, -0.2),  # Positionne au-dessus de l'inventaire
        scale=(2, 1.5),

    )

    # Champ de saisie pour taper son texte (cache par defaut)
    chat_input = InputField(
        enabled=False,
        position=(0, -0.45),  # Au centre bas de l'ecran
        scale=(0.5, 0.04),
        max_lines=1
    )
    craft_input_2.stack_text = Text(
        parent=craft_input_2,
        text="",
        scale=27,  # Augmente si c'est trop petit (Ursina scale est relatif au parent)
        position=(0.2, -0.2, -0.1),  # Le Z à -0.1 le met DEVANT le bouton
        origin=(0, 0),
        color=color.white,
        # On s'assure que le texte ne bouge pas
        add_to_scene_entities=False
    )
    craft_output.stack_text = Text(
        parent=craft_output,
        text="",
        scale=27,  # Augmente si c'est trop petit (Ursina scale est relatif au parent)
        position=(0.2, -0.2, -0.1),  # Le Z à -0.1 le met DEVANT le bouton
        origin=(0, 0),
        color=color.white,
        # On s'assure que le texte ne bouge pas
        add_to_scene_entities=False
    )

    # Petit texte d'instruction
    Text(parent=crafting_ui, text="Crafting", origin=(0, 0), y=0.2)
    # Viseur (Crosshair)
    crosshair = Entity(parent=game_ui, model='quad', texture='Assets/BaseTextures/crosschair.png', scale=0.2, color=color.white)
    lumiere_ambiance = AmbientLight()
    # Barre de vie
    global item_tooltip
    item_tooltip = Text(
        text='',
        parent=game_ui,
        size=0.02,
        color=color.white,
        origin=(0, 0),
        y=-0.30,  # Positionné juste au-dessus de la barre d'inventaire
        background=True
    )

    for i in range(9):
        slot = Button(
            parent=game_ui,
            model='quad',
            scale=(0.06, 0.06),
            texture='Assets/BaseTextures/slot.png',
            position=(-0.28 + (i * 0.07), -0.47),
        )
        slot.is_empty = True
        slot.item_name = ""
        slot.stack = 0


        # --- CONFIGURATION DU TEXTE ---
        slot.stack_text = Text(
            parent=slot,
            text="",
            scale=27,  # Augmente si c'est trop petit (Ursina scale est relatif au parent)
            position=(0.2, -0.2, -0.1),  # Le Z à -0.1 le met DEVANT le bouton
            origin=(0, 0),
            color=color.white,
            # On s'assure que le texte ne bouge pas
            add_to_scene_entities=False
        )
        inventory_slots.append(slot)
        slot.on_click = lambda s=slot: item_click(s)

    update_hotbar()
    update_item_tooltip()
    # --- MENU ---

    main_menu = Entity(parent=camera.ui, enabled=False)
    arriereplan = Sprite('main-menu.png', parent=main_menu, scale=1.5, z=1)
    # À mettre dans main(), après crafting_ui
    global trader_ui
    trader_ui = Entity(parent=camera.ui, enabled=False)
    trader_bg = Entity(parent=trader_ui, model='quad', scale=(0.8, 0.5), texture='main-menu.png', z=1)
    Text(parent=trader_ui, text="Trader", y=0.2, origin=(0, 0), z=0.9)
    global trader_scroll_area
    trader_scroll_area = ScrollingPane(parent=trader_ui, y=0, x=-0.2)
    # Bouton pour fermer
    close_shop = Button(parent=trader_ui, text="X", scale=0.05, x=0.37, y=0.22, color=color.red, z=0.9, texture="main-menu.png")
    close_shop.on_click = lambda: setattr(trader_ui, 'enabled', False) or setattr(mouse, 'locked', True) or setattr(crosshair, 'visible', True) or setattr(player, 'enabled', True) or Onmenu_disok()


    title_text = Text(
        text='CUBICA',
        parent=main_menu,
        font='Assets/Fonts/Minecraftory.ttf',
        scale=5,
        y=0.3,
        origin=(0, 0)
    )
    hearts_ui = Text(
        parent=game_ui,
        text='',
        position=(-0.2, -0.35),  # Ajuste selon la position de ton inventaire
        scale=2.5,  # Rend les coeurs bien visibles
        color=color.red,  # Coeurs rouges !
        origin=(0, 0)
    )
    play_button = Button(
        text='Play',
        parent=main_menu,
        scale=(0.2, 0.05),
        y=0.05,
        color=color.azure
    )

    quit_button = Button(
        text='Exit',
        parent=main_menu,
        scale=(0.2, 0.05),
        y=-0.05,
        color=color.red
    )
    def exitandsave():
        global is_saving_now
        saveGame()



    # Actions des boutons
    play_button.on_click = start_game
    quit_button.on_click = exitandsave

    mouse.visible = True
    mouse.locked = False
    # Cliquer sur un slot d'entrée le vide


    # Cliquer sur la sortie donne l'objet
    def collect_craft():
        if not craft_output.is_empty:
            if add_to_inventory(craft_output.item_name, craft_output.stack):
                clear_slot(craft_input_1)
                clear_slot(craft_input_2)
                clear_slot(craft_output)
                craft_output.color = color.gray
    def get1():
        if not craft_input_1.is_empty:
            if add_to_inventory(craft_input_1.item_name, craft_input_1.stack):
                clear_slot(craft_input_1)
                check_craft()


    def get2():
        if not craft_input_2.is_empty:
            if add_to_inventory(craft_input_2.item_name, craft_input_2.stack):
                clear_slot(craft_input_2)
                check_craft()

    demarrer_transition()
    craft_output.on_click = collect_craft
    craft_input_1.on_click = get1
    craft_input_2.on_click = get2
    setup_hearts_ui()  # Cree les 10 objets graphiques
    update_hearts_display()  # Donne la bonne texture initiale
    epppliatcztdfftdfetg = application




    update_hotbar()
    update_item_tooltip()
    #MODS IMPORTATION

    app.run()



def start_game():

    """
    Gère le clic sur le bouton Play : charge la partie existante
    ou génère un nouveau monde si aucune sauvegarde n'est présente.
    """
    global player, _on_menu_, hand
    hand = Entity(
        parent=camera.ui,
        model='cube',
        texture='Assets/BaseTextures/hand.png',
        scale=(0.1, 0.25, 0.1),  # On deplace le point d ancrage au bas du cube
        position=(0.6, -0.5),  # On le cale bien en bas a droite
        rotation=(30, -20, 0)  # En bas à droite de l'écran
    )
    _on_menu_ = False
    player = FirstPersonController()
    player.enabled = False
    player.xp = 0
    player.cursor.visible = False  # Affiche le réticule au centre
    player.gravity = 1
    player.jump_height = 0.75
    player.speed = 8
    player.is_busy = False
    import os
    global main_menu, crosshair
    # 1. Fermer le menu et activer les contrôles de base
    main_menu.enabled = False
    loadGameMenu()


def demarrer_transition():
    global main_menu
    loading_screen = Entity(parent=camera.ui, enabled=True)
    background_color_of_start = Entity(z=10, model="quad", parent=loading_screen, scale=(window.aspect_ratio * 2, 2),
                                       color=color.azure)

    # On garde des references sur les textes pour pouvoir changer leur alpha
    t1 = Text(
        text='W',
        parent=loading_screen,
        font='Assets/Fonts/Minecraftory.ttf',
        scale=10,
        y=0.3,
        z=1,
        origin=(0, 0)
    )
    t2 = Text(
        text='STUDIO',
        parent=loading_screen,
        font='Assets/Fonts/Minecraftory.ttf',
        scale=5,
        z=1,
        y=0.1,
        origin=(0, 0)
    )
    t3 = Text(
        text='PRESENTS',
        parent=loading_screen,
        font='Assets/Fonts/Minecraftory.ttf',
        scale=3,
        z=1,
        y=-0.1,
        origin=(0, 0)
    )
    ttxxtt = Text(
        text='',
        parent=loading_screen,
        font='Assets/Fonts/Minecraftory.ttf',
        scale=5,
        z=1,
        y=-0.3,
        origin=(0, 0)
    )

    ttxxtt.text = "CUBICA"
    ttxxtt.color = color.white
    ttxxtt.alpha = 0

    sequence = Sequence()
    musique_chargement = Audio('Assets/Sounds/WSTUDIO-introduction.wav', loop=False, autoplay=True)
    musique_chargement.author = "Bowser245"
    musique_chargement.copyright = "(c)2026. W Studio. All rights reserveds."
    musique_chargement.volume = 0.5
    # Attendre avant de demarrer l animation
    sequence.append(Wait(10))

    # Effet de fondu (fade in) sur CUBICA
    sequence.append(Func(ttxxtt.fade_in, value=1, duration=1))

    # Attendre avant de lancer le fondu de fermeture
    sequence.append(Wait(3))

    # 1. On lance le fondu de disparition (fade out) de tous les elements
    # On lance le fondu de disparition (fade out) de tous les elements
    def lancer_fondu_fermeture():
        # Remplacement de color.transparent par color.clear
        background_color_of_start.animate_color(color.clear, duration=1.5)
        t1.animate_color(color.clear, duration=1.5)
        t2.animate_color(color.clear, duration=1.5)
        t3.animate_color(color.clear, duration=1.5)
        ttxxtt.animate_color(color.clear, duration=1.5)
        print("Debut du fondu de fermeture")

    sequence.append(Func(lancer_fondu_fermeture))

    # 2. On attend la fin de l animation de fondu (1.5 seconde)
    sequence.append(Wait(1.5))

    # 3. Transition finale et activation du menu principal
    def changer_ecran():
        if loading_screen:
            loading_screen.enabled = False
        if main_menu:
            main_menu.enabled = True
        print("Fin de la transition")

    sequence.append(Func(changer_ecran))

    sequence.start()

#def animer_texte():
   # # Déclaration explicite des variables globales
   # global ttxxtt, main_menu, loading_screen
#
   # mot = "CUBICA"
   # sequence = Sequence()
#
   # # Vérification de sécurité : si l'un est None, on arrête tout pour éviter le crash
   # if loading_screen is None or main_menu is None:
   #     print("Erreur : loading_screen ou main_menu n'est pas defini !")
   #     return
#
   # son = Audio('Assets/Sounds/dragon-studio-clicking-keyboard-asmr-sfx-356115.mp3', autoplay=False)
   # sequence.append(Func(son.play))
#
   # for i in range(len(mot) + 1):
   #     sequence.append(Func(setattr, ttxxtt, 'text', mot[:i]))
   #     sequence.append(Wait(1.33))
#
   # # Utilisation d'une fonction lambda ou d'une fonction dédiée pour la transition
   # def transition():
   #     if loading_screen: loading_screen.enabled = False
   #     if main_menu: main_menu.enabled = True
#
   # sequence.append(Func(transition))
   # sequence.start()

# Appelle cette fonction lors du lancement de ton écran de chargement
def restart():
    from Bin import drop
    ttxxtt = None
    loading_screen = None
    hearts_sprites = []
    from Bin import trades
    trader_offers = trades.trader_offers
    shop_structure = {
        1: {  # Couche sol
            1: {1: "plank", 2: "plank", 3: "plank"},
            2: {1: "plank", 2: "plank", 3: "plank"},
            3: {1: "plank", 2: "plank", 3: "plank"},
        },
        2: {  # Murs et Trader
            1: {1: "plank", 2: None, 3: "plank"},
            2: {1: None, 2: "trader", 3: None},
            3: {1: "plank", 2: None, 3: "plank"},
        },
        3: {  # Murs et Déco
            1: {1: "plank", 2: None, 3: "plank"},
            2: {1: None, 2: "hay-bale", 3: None},
            3: {1: "plank", 2: None, 3: "plank"},
        },
        4: {  # Toit
            1: {1: "wool", 2: "wool", 3: "wool"},
            2: {1: "wool", 2: "wool", 3: "wool"},
            3: {1: "wool", 2: "wool", 3: "wool"},
        }
    }
    import random
    import math
    loots_table = drop.loots_table
    import math
    from perlin_noise import PerlinNoise

    world_data = {}
    pickaxe_speeds = drop.pickaxe_speeds
    required = drop.require
    damagex = drop.sword_multipliers
    # Cooldown d'attaque du joueur
    last_attack_time = 0
    ATTACK_COOLDOWN = 0.5  # Temps en secondes entre deux coups (ici 0.5s)
    from Bin import drop
    drops = drop.drops
    spawn_timer = 0
    lasted_tooltip = ""
    temps_jeu = 0
    vitesse_temps = 0.5
    from Bin.drop import shiled_recharging, shiled_time
    is_blocking = False
    shield_timer = 0.0
    cooldown_timer = 0.0
    current_sword = "none"
    custom_save_ui = []  # Liste pour tout détruire d'un coup
    input_field = None
    nom_sauvegarde = ""
    is_saving_now = False
    worldexist = None
    worldpath = ""
    block_properties = {}
    player = None
    main_menu = None
    hand = None
    selected_slot = 0
    inventory_slots = []
    loaded_modules = {}
    title_text = None
    play_button = None
    game_ui = None  # Le parent de toute l'UI en jeu
    recipes = recipe.recipes
    craft_input_1 = None
    craft_input_2 = None
    craft_output = None
    crafting_ui = None
    epppliatcztdfftdfetg = None
    arriereplan = None
    filePath = 'Assets/items.cbdata'
    CHUNK_SIZE = 8
    RENDER_DISTANCE = 1  # Rayon de chunks chargés autour du joueur
    chunks = {}  # {(cx, cz): [liste_des_voxels]}
    # Statistiques du joueur
    player_hp = 20
    player_max_hp = 20
    last_player_damaged_time = 0
    PLAYER_DAMAGED_COOLDOWN = 1.0  # Le joueur ne peut prendre des degats qu'une fois par seconde
    regen_timer = 0
    REGEN_COOLDOWN = 4.0  # Le joueur recupere de la vie toutes les 4 secondes
    REGEN_AMOUNT = 1
    pseudo_joueur = "Player"
    main()

def reload():
    print("Redemarrage du script en cours")
    # Recupere le chemin de l'interpreteur Python et les arguments du script
    import sys
    import os
    python = sys.executable
    os.execv(python, [python] + sys.argv)
    sys.exit()



if __name__ == "__main__":

    try:
        main()
    except Exception as e:
        from Assets.UI import uicrash
        uicrash.main(str(e), reload)

