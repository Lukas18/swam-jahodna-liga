"""Slovak UI labels with stable internal widget values and unchanged stored data."""
import re
from copy import deepcopy
from functools import wraps
import streamlit

# Translation keys remain English so switching languages never changes record IDs,
# categories, navigation values, editor column keys or scoring rules.
SK = {
    'Language': 'Jazyk', 'Home': 'Domov', 'Leagues': 'Ligy', 'Tournaments': 'Turnaje',
    'Statistics': 'Štatistiky', 'Admin': 'Administrácia', 'Explore': 'Navigácia',
    'League leaderboard': 'Poradie ligy', 'Overall standings': 'Celkové poradie',
    'Leaderboard view': 'Zobrazenie výsledkov', 'Score relative to par': 'Skóre voči paru',
    'Handicap adjusted': 'Skóre s handicapom', 'Category': 'Kategória', 'All': 'Všetky',
    'Place': 'Poradie', 'Name': 'Meno', 'Player': 'Hráč', 'Players': 'Hráči', 'Points': 'Body',
    'Total points': 'Celkové body', 'Tournaments attended': 'Odohrané turnaje',
    'Rounds': 'Kolá', 'Throws': 'Hody', 'HCP adjusted': 'Skóre s HCP', 'Complete': 'Dokončené',
    'Recent tournaments': 'Posledné turnaje', 'League': 'Liga', 'League tournaments': 'Turnaje ligy',
    'Placement points': 'Bodovanie podľa umiestnenia', 'Tournament': 'Turnaj', 'Date': 'Dátum',
    'Public results · read-only': 'Verejné výsledky · iba na čítanie', 'Refresh results': 'Obnoviť výsledky',
    'Local competition. Every round counts.': 'Miestna liga. Každé kolo sa počíta.',
    'Points awarded per category.': 'Body sa prideľujú v každej kategórii samostatne.',
    'Points awarded across all players.': 'Body sa prideľujú v spoločnom poradí všetkých hráčov.',
    'No results yet.': 'Zatiaľ nie sú žiadne výsledky.',
    'Standings will appear after the first recorded round.': 'Poradie sa zobrazí po zapísaní prvého kola.',
    'The admin can create the first league and tournament.': 'Administrátor môže vytvoriť prvú ligu a turnaj.',
    'Points follow the selected leaderboard view. Attendance counts tournaments with a recorded round, including incomplete tournaments. Tied places share the same medal and use T (for example T3, T3, 5).':
        'Body zodpovedajú zvolenému zobrazeniu výsledkov. Účasť sa počíta za turnaje so zapísaným kolom, aj za nedokončené turnaje. Pri zhode hráči zdieľajú medailu a poradie s T (napríklad T3, T3, 5).',
    'Completed players only': 'Iba hráči s dokončenými kolami', 'Round scorecards': 'Výsledky jednotlivých kôl',
    'Place is the player’s category rank, even in the combined view. Lower scores rank higher. Incomplete players are excluded by default. Raw totals across different hole counts are not directly comparable.':
        'Poradie patrí ku kategórii hráča aj v spoločnom zobrazení. Nižšie skóre znamená lepšie umiestnenie. Hráči s nedokončenými kolami sa predvolene nezobrazujú.',
    'Totals-only result — hole scores unavailable.': 'Zapísaný je iba celkový výsledok — skóre jamiek nie je dostupné.',
    'Tournament statistics': 'Štatistiky turnaja', 'Statistics category': 'Kategória štatistík',
    'Recorded rounds': 'Zapísané kolá', 'Hole scores': 'Zapísané skóre jamiek',
    'Average throws per round': 'Priemerný počet hodov na kolo', 'Average +/− par per round': 'Priemerné skóre voči paru na kolo',
    'Average throws': 'Priemerné hody', 'Average +/− par': 'Priemer voči paru',
    'Course overview': 'Prehľad ihrísk', 'Layout overview': 'Prehľad layoutov', 'Hole statistics': 'Štatistiky jamiek',
    'Hole': 'Jamka', 'Holes': 'Jamky', 'Length (m)': 'Dĺžka (m)', 'Scores': 'Počet výsledkov',
    'Ace %': 'Ace %', 'Albatross or better %': 'Albatross a lepšie %', 'Eagle %': 'Eagle %',
    'Birdie %': 'Birdie %', 'Par %': 'Par %', 'Bogey %': 'Bogey %', 'Double bogey %': 'Double bogey %',
    'Triple bogey or worse %': 'Triple bogey a horšie %', 'Course': 'Ihrisko', 'Layout': 'Layout',
    'No recorded results match these filters.': 'Pre zvolené filtre nie sú zapísané žiadne výsledky.',
    'Round averages include totals-only results. Different hole counts and layouts affect raw totals; category and layout breakdowns are below. All recorded rounds are included, even for players who have not completed a tournament.':
        'Priemery kôl zahŕňajú aj výsledky bez skóre jednotlivých jamiek. Počet jamiek a layout ovplyvňujú celkové hody; rozdelenie nájdete nižšie. Zahrnuté sú všetky zapísané kolá, aj z nedokončených turnajov.',
    'Heat map: green = below par; warm orange = above par. Averages within ±0.25 of par stay neutral; tint steps end at 0.75 and 1.50 throws from par. Outcome percentages use three strengths: >0–25%, >25–50%, >50%. Par percentages stay neutral.':
        'Farebná mapa: zelená = pod parom, oranžová = nad parom. Priemery do ±0,25 od paru sú neutrálne; hranice odtieňov sú 0,75 a 1,50 hodu od paru. Percentá používajú tri intenzity: >0–25 %, >25–50 %, >50 %. Par ostáva neutrálny.',
    'These results have totals only. Import or enter hole scores to see hole averages and outcome percentages.':
        'Tieto výsledky obsahujú iba celkové skóre. Na zobrazenie priemerov a percent zapíšte alebo importujte skóre jamiek.',
    'Hole averages and percentages use actual recorded hole scores across the selected scope. Layouts, categories and historical par/length configurations stay separate. Aces are counted separately from other outcomes; percentages sum to 100% per hole.':
        'Priemery a percentá vychádzajú zo zapísaných skóre jamiek vo zvolenom rozsahu. Layouty, kategórie a historické hodnoty paru a dĺžky sú oddelené. Ace sa počíta samostatne; súčet percent na jamke je 100 %.',
    'Results scope': 'Rozsah výsledkov', 'All time': 'Celá história', 'All-time statistics': 'Štatistiky za celú históriu',
    'All courses': 'Všetky ihriská', 'All layouts': 'Všetky layouty',
    'Administration': 'Administrácia', 'Admin password': 'Heslo administrátora', 'Sign in': 'Prihlásiť sa',
    'Sign out': 'Odhlásiť sa', 'Incorrect password.': 'Nesprávne heslo.',
    'Too many attempts. Try again in a minute.': 'Príliš veľa pokusov. Skúste to o minútu.',
    'Signed in. Manage all league data here.': 'Ste prihlásený. Tu môžete spravovať všetky údaje ligy.',
    'Administrator · session expires after 8 hours': 'Administrátor · prihlásenie platí 8 hodín',
    'Admin editing is disabled until an admin password is configured in Streamlit secrets or DISCGOLF_ADMIN_PASSWORD.':
        'Úpravy sú vypnuté, kým nenastavíte heslo administrátora v Streamlit secrets alebo DISCGOLF_ADMIN_PASSWORD.',
    'Local JSON storage is active. Before cloud deployment, configure GitHub storage to preserve edits through restarts.':
        'Používa sa lokálne úložisko JSON. Pred nasadením do cloudu nastavte GitHub úložisko, aby sa zmeny zachovali pri reštarte.',
    'Persistent GitHub JSON storage is active.': 'Používa sa trvalé GitHub úložisko JSON.',
    'Manage': 'Správa', 'Courses & layouts': 'Ihriská a layouty', 'Tournaments & scores': 'Turnaje a výsledky',
    'Categories': 'Kategórie', 'Settings': 'Nastavenia', 'Backup & restore': 'Záloha a obnova',
    'Manage scores': 'Správa výsledkov', 'Manual entry': 'Ručné zadanie', 'uDisc import': 'Import z uDisc',
    'Application settings': 'Nastavenia aplikácie', 'Application title': 'Názov aplikácie',
    'Active league': 'Aktívna liga', 'No leagues yet': 'Zatiaľ žiadne ligy', 'Save settings': 'Uložiť nastavenia',
    'Home shows standings for this league. Only one league is active at a time.':
        'Na úvodnej stránke sa zobrazuje poradie tejto ligy. Súčasne môže byť aktívna iba jedna liga.',
    'Enter an application title.': 'Zadajte názov aplikácie.', 'Changes saved.': 'Zmeny boli uložené.',
    'Sign in as administrator to save changes.': 'Na uloženie zmien sa prihláste ako administrátor.',
    'Create league': 'Vytvoriť ligu', 'Edit league & points': 'Upraviť ligu a bodovanie',
    'Number of places awarded points': 'Počet bodovaných umiestnení', 'League name': 'Názov ligy',
    'Award tournament points': 'Prideľovanie bodov', 'Within each category': 'V každej kategórii',
    'Across all players': 'Spoločne pre všetkých hráčov', 'Ties': 'Zhoda výsledkov',
    'Share occupied-place points': 'Rozdeliť body za obsadené miesta', 'Same points for the tied place': 'Rovnaké body za zhodné poradie',
    'Unlisted places receive zero points. Only completed tournaments award points. Editing rules recalculates standings.':
        'Nebodované miesta získajú nula bodov. Body sa prideľujú iba za dokončené turnaje. Zmena pravidiel prepočíta poradie.',
    'Save league': 'Uložiť ligu', 'Enter a name and a whole-number points value for every place.': 'Zadajte názov a celé číslo bodov pre každé miesto.',
    'Edit player': 'Upraviť hráča', 'Add new player': 'Pridať hráča', 'First name': 'Meno', 'Last name': 'Priezvisko',
    'Default category': 'Predvolená kategória', 'Handicap per round': 'Handicap na kolo', 'uDisc username': 'Používateľské meno uDisc',
    'Used to match imported results. Matching ignores case and surrounding spaces.': 'Slúži na priradenie importovaných výsledkov. Veľkosť písmen a okolité medzery sa ignorujú.',
    'Handicap adjusted score = throws − par − handicap. Defaults apply to new results; saved rounds retain their recorded values.':
        'Skóre s handicapom = hody − par − handicap. Predvolené hodnoty sa použijú pri nových výsledkoch; zapísané kolá si zachovajú pôvodné údaje.',
    'Save player': 'Uložiť hráča', 'Delete player': 'Odstrániť hráča',
    'Players registered in tournaments or with scores cannot be deleted.': 'Hráčov prihlásených na turnaj alebo so zapísanými výsledkami nemožno odstrániť.',
    'Create layout': 'Vytvoriť layout', 'Edit layout': 'Upraviť layout', 'Hole configuration': 'Konfigurácia jamiek',
    'Default — all categories unless overridden': 'Predvolená — pre kategórie bez vlastného nastavenia',
    'Number of holes': 'Počet jamiek', 'Layout name': 'Názov layoutu', 'Save hole configuration': 'Uložiť konfiguráciu jamiek',
    'Choose the hole count first, then edit pars and lengths. Each category can have its own count. Lengths are in metres; 0 means unknown.':
        'Najprv zvoľte počet jamiek, potom upravte pary a dĺžky. Každá kategória môže mať vlastný počet jamiek. Dĺžky sú v metroch; 0 znamená neznámu dĺžku.',
    'Remove override and use default holes': 'Odstrániť vlastné nastavenie a použiť predvolené jamky',
    'Courses → Layouts': 'Ihriská → Layouty', 'Create course': 'Vytvoriť ihrisko', 'Edit course': 'Upraviť ihrisko',
    'Course name': 'Názov ihriska', 'Description': 'Popis', 'Save course': 'Uložiť ihrisko',
    'Enter a course name.': 'Zadajte názov ihriska.', 'Category-specific holes': 'Jamky pre zvolenú kategóriu',
    'Uses the default layout holes': 'Používajú sa predvolené jamky layoutu', 'Layout statistics': 'Štatistiky layoutu',
    'No hole-by-hole scores recorded for this layout and category yet.': 'Pre tento layout a kategóriu zatiaľ nie sú zapísané skóre jamiek.',
    'Percentages use recorded hole scores only. An ace is counted separately from an eagle/birdie, so outcome percentages sum to 100%. Historical tee configurations with different par or length have separate rows. Totals-only results are excluded from hole statistics.':
        'Percentá vychádzajú iba zo zapísaných skóre jamiek. Ace sa počíta oddelene od Eagle/Birdie, súčet je teda 100 %. Historické konfigurácie s iným parom alebo dĺžkou sú v samostatných riadkoch. Celkové výsledky bez jamiek sa nezahŕňajú.',
    'Create tournament': 'Vytvoriť turnaj', 'Edit tournament': 'Upraviť turnaj', 'Tournament name': 'Názov turnaja',
    'Course / layout': 'Ihrisko / layout', 'Save tournament': 'Uložiť turnaj',
    'Create a league and a course layout before creating a tournament.': 'Pred vytvorením turnaja vytvorte ligu a layout ihriska.',
    'Layout, rounds and categories are locked while this tournament has registered players or scores.':
        'Layout, kolá a kategórie nemožno meniť, pokiaľ turnaj obsahuje prihlásených hráčov alebo výsledky.',
    'Enter a name and select at least one category.': 'Zadajte názov a vyberte aspoň jednu kategóriu.',
    'Tournament players': 'Hráči turnaja', 'Players to add': 'Hráči na pridanie', 'Registration category': 'Kategória prihlášky',
    'Player default': 'Predvolená hodnota hráča', 'Add selected players': 'Pridať vybraných hráčov',
    'Use each player’s default category and handicap, or choose a category override for this selection.':
        'Použite predvolenú kategóriu a handicap hráčov alebo zvoľte vlastnú kategóriu pre tento výber.',
    'All players are registered. Add more players under Admin → Players.': 'Všetci hráči sú prihlásení. Ďalších pridajte cez Administrácia → Hráči.',
    'Edit registration': 'Upraviť prihlášku', 'Registered player': 'Prihlásený hráč', 'Tournament category': 'Kategória na turnaji',
    'Tournament handicap': 'Handicap na turnaji', 'Save registration': 'Uložiť prihlášku', 'Remove registration': 'Odstrániť prihlášku',
    'Players with scores retain their registration. Remove their recorded rounds first to change category, handicap or registration.':
        'Prihlášky hráčov s výsledkami sú uzamknuté. Pred zmenou kategórie, handicapu alebo prihlášky odstráňte ich zapísané kolá.',
    'Enter scores': 'Zadať výsledky', 'Round number': 'Číslo kola', 'Save': 'Uložiť', 'Status': 'Stav',
    'Recorded': 'Zapísané', 'Not recorded': 'Nezapísané', 'Totals only': 'Iba celkové výsledky',
    'Add players to this tournament before entering scores.': 'Pred zadaním výsledkov pridajte hráčov do turnaja.',
    'Players are rows; holes are columns. Tick Save for rows to record. Unplayed scores stay blank. Saving a recorded row replaces that round. Tables are separated by category so junior hole counts stay correct.':
        'Hráči sú v riadkoch, jamky v stĺpcoch. Označte Uložiť pri požadovaných riadkoch. Neodohrané skóre ostáva prázdne. Uloženie zapísaného riadka nahradí dané kolo. Tabuľky sú oddelené podľa kategórie a počtu jamiek.',
    'Round to remove': 'Kolo na odstránenie', 'Confirm removal of this round': 'Potvrdiť odstránenie tohto kola',
    'Remove recorded round': 'Odstrániť zapísané kolo', 'Remove a recorded round': 'Odstrániť zapísané kolo',
    'Import uDisc results': 'Importovať výsledky uDisc', 'uDisc export': 'Export uDisc', 'Worksheet': 'Hárok',
    'Header row (1-based)': 'Riadok hlavičky (od 1)', '(not mapped)': '(nepriradené)',
    'Excel .xlsx or CSV: one player per row, optionally with a round column. Match by uDisc username, never by display name. Add unknown usernames in Players first.':
        'Excel .xlsx alebo CSV: jeden hráč na riadok, voliteľne so stĺpcom kola. Výsledky sa priraďujú podľa používateľského mena uDisc. Neznáme mená najprv pridajte v správe hráčov.',
    'No rows in this worksheet.': 'Tento hárok neobsahuje žiadne riadky.', 'uDisc username column': 'Stĺpec používateľského mena uDisc',
    'Category column': 'Stĺpec kategórie', 'Handicap column': 'Stĺpec handicapu', 'Round column': 'Stĺpec kola',
    'Category when not mapped': 'Kategória bez priradeného stĺpca', 'Round when not mapped': 'Kolo bez priradeného stĺpca',
    'Import detail': 'Podrobnosť importu', 'Hole-by-hole scores': 'Skóre jednotlivých jamiek',
    'Absolute total throws column': 'Stĺpec celkového počtu hodov', 'Map hole score columns': 'Priradenie stĺpcov skóre jamiek',
    'Map actual throw counts, not scores relative to par. Optional total checks that hole scores add up. Totals-only imports do not generate hole statistics.':
        'Priraďte skutočné počty hodov. Voliteľný celkový počet overí súčet jamiek. Import iba celkových výsledkov nevytvára štatistiky jamiek.',
    'Each hole needs a different score column.': 'Každá jamka potrebuje samostatný stĺpec skóre.', 'Import preview': 'Náhľad importu',
    'Allow replacement of the existing rounds shown above': 'Povoliť nahradenie existujúcich kôl uvedených vyššie',
    'Confirm import': 'Potvrdiť import', 'Row': 'Riadok', 'Action': 'Akcia', 'Replace': 'Nahradiť', 'Add': 'Pridať',
    'New category code': 'Kód novej kategórie', 'Add category': 'Pridať kategóriu', 'Category to remove': 'Kategória na odstránenie',
    'Remove category': 'Odstrániť kategóriu', 'Category already exists.': 'Kategória už existuje.',
    'Use a category code of up to 20 letters, numbers, underscores or hyphens.': 'Kód kategórie môže mať najviac 20 písmen, číslic, podčiarkovníkov alebo pomlčiek.',
    'A category can be removed once it is no longer used by players, tournaments or layout overrides.':
        'Kategóriu možno odstrániť, keď sa už nepoužíva pri hráčoch, turnajoch ani vlastných nastaveniach layoutov.',
    'Download CSV': 'Stiahnuť CSV', 'Download hole statistics': 'Stiahnuť štatistiky jamiek',
    'Download course overview': 'Stiahnuť prehľad ihrísk', 'Download layout overview': 'Stiahnuť prehľad layoutov',
    'Download full JSON backup': 'Stiahnuť úplnú zálohu JSON', 'Restore JSON backup': 'Obnoviť zálohu JSON',
    'Replace all current data with this backup': 'Nahradiť všetky aktuálne údaje touto zálohou', 'Restore backup': 'Obnoviť zálohu',
    'Hole number': 'Číslo jamky', 'number': 'Jamka', 'par': 'Par', 'length': 'Dĺžka (m)', 'throws': 'Hody',
    'Configuration': 'Konfigurácia', 'Score': 'Skóre', 'Round': 'Kolo',
}

SK.update({
    'Combined statistics show one row per hole. Par and known lengths are sample-weighted averages; relative scores and outcome percentages use each score’s recorded par.': 'Súhrnné štatistiky zobrazujú jeden riadok na jamku. Par a známe dĺžky sú priemery vážené počtom výsledkov; skóre voči paru a percentá výsledkov sa počítajú podľa paru zapísaného pri každom skóre.',
    'Attendance counts tournaments with a recorded round, including incomplete tournaments. Tied places share the same medal and use T (for example T3, T3, 5).': 'Účasť sa počíta za turnaje so zapísaným kolom, aj za nedokončené turnaje. Pri zhode hráči zdieľajú medailu a poradie s T (napríklad T3, T3, 5).',
    'Percentages use all recorded hole scores. Historical tee configurations with different par or length have separate rows. Totals-only results are excluded from hole statistics.': 'Percentá sa počítajú zo všetkých zapísaných skóre jamiek. Historické konfigurácie s iným parom alebo dĺžkou majú samostatné riadky. Výsledky bez skóre jamiek sa do štatistík jamiek nezahŕňajú.',
    'Round averages include totals-only results and all recorded rounds, including incomplete tournaments.': 'Priemery zahŕňajú aj výsledky bez skóre jamiek a všetky zapísané kolá vrátane nedokončených turnajov.',
    'Hole averages and percentages use all recorded hole scores in the selected scope. Layouts, categories and historical par/length configurations stay separate.': 'Priemery a percentá jamiek sa počítajú zo všetkých zapísaných skóre vo vybranom rozsahu. Layouty, kategórie a historické konfigurácie paru a dĺžky zostávajú oddelené.',
    'Edit layout & category holes': 'Upraviť layout a jamky kategórií',
    'No result rows found.': 'Nenašli sa žiadne riadky s výsledkami.',
    'Edit or remove a tournament registration': 'Upraviť alebo odstrániť prihlášku na turnaj',
    'League to edit': 'Liga na úpravu', 'Tournament to manage': 'Turnaj na správu',
    'Layout name is required.': 'Názov layoutu je povinný.',
    'Category is not enabled for this tournament.': 'Táto kategória nie je povolená pre daný turnaj.',
    'Category and handicap cannot change while this player has tournament scores.': 'Kategóriu a handicap nemožno meniť, pokiaľ má hráč na turnaji výsledky.',
    'Select Save for at least one player row.': 'Označte Uložiť aspoň pri jednom hráčovi.',
    'Unknown or duplicate player in score grid.': 'Neznámy alebo duplicitný hráč v tabuľke výsledkov.',
    'A layout needs at least one hole.': 'Layout musí obsahovať aspoň jednu jamku.',
    'Length cannot be negative.': 'Dĺžka nemôže byť záporná.',
    'First and last name are required.': 'Meno a priezvisko sú povinné.',
    'First name is required.': 'Meno je povinné.',
    'Layout used for these results': 'Layout použitý pre tieto výsledky',
    'Choose a layout': 'Vyberte layout',
    'Choose a layout to preview the import.': 'Pre náhľad importu vyberte layout.',
    'Choose a valid import layout.': 'Vyberte platný layout pre import.',
    'A tournament with recorded scores must keep its existing layout.': 'Turnaj so zapísanými výsledkami musí zachovať svoj pôvodný layout.',
    'Scores relative to par are calculated from the selected layout and its category holes. Spreadsheet relative scores are ignored. The layout is saved with the tournament when you confirm the import.': 'Skóre voči paru sa vypočíta podľa vybraného layoutu a jamiek kategórie. Skóre voči paru z tabuľky sa ignoruje. Layout sa uloží do turnaja pri potvrdení importu.',
    'Optional for players using a single name.': 'Nepovinné pre hráčov používajúcich iba jedno meno.',
    'Score relative to par column': 'Stĺpec skóre voči paru',
    'Exported total par': 'Celkový par v exporte',
    'Map an absolute total to check the exported score relative to par.': 'Na kontrolu exportovaného skóre voči paru priraďte celkový počet hodov.',
    'This export contains hole throw counts, not hole pars. Select the tournament layout explicitly. Exported totals and scores relative to par are checked against the category layout.': 'Tento export obsahuje počty hodov na jamkách, nie pary jamiek. Layout vyberte v nastavení turnaja. Celkové výsledky a skóre voči paru z exportu sa kontrolujú podľa layoutu kategórie.',
    'Choose an active category.': 'Vyberte aktívnu kategóriu.',
    'This uDisc username already belongs to another player.': 'Toto používateľské meno uDisc už patrí inému hráčovi.',
    'Use this player’s registered category and handicap.': 'Použite kategóriu a handicap z prihlášky hráča.',
    'Use the same category and handicap as this player’s other tournament rounds.': 'Použite rovnakú kategóriu a handicap ako v ostatných kolách hráča na tomto turnaji.',
    'Provide scores for exactly the holes in this category’s layout.': 'Zadajte skóre presne pre jamky layoutu tejto kategórie.',
    'Total does not match the sum of hole scores.': 'Celkový výsledok nezodpovedá súčtu skóre jamiek.',
    'Provide hole scores or an absolute total number of throws.': 'Zadajte skóre jamiek alebo celkový počet hodov.',
    'Unsupported backup format.': 'Nepodporovaný formát zálohy.',
    'Categories must be unique, non-empty names.': 'Názvy kategórií musia byť jedinečné a neprázdne.',
    'Invalid application settings.': 'Neplatné nastavenia aplikácie.',
    'Application title must contain 1 to 100 characters.': 'Názov aplikácie musí mať 1 až 100 znakov.',
    'Unknown active league.': 'Neznáma aktívna liga.',
    'Invalid player name or category.': 'Neplatné meno alebo kategória hráča.',
    'Duplicate uDisc username.': 'Duplicitné používateľské meno uDisc.',
    'Course name is required.': 'Názov ihriska je povinný.',
    'Invalid layout.': 'Neplatný layout.', 'Unknown layout category.': 'Neznáma kategória layoutu.',
    'League name and placement points are required.': 'Názov ligy a bodovanie umiestnení sú povinné.',
    'Invalid league scoring settings.': 'Neplatné nastavenia bodovania ligy.',
    'Points cannot be negative.': 'Body nemôžu byť záporné.',
    'Invalid tournament links or name.': 'Neplatné prepojenia alebo názov turnaja.',
    'Invalid tournament categories.': 'Neplatné kategórie turnaja.',
    'Invalid tournament registrations.': 'Neplatné prihlášky na turnaj.',
    'Invalid tournament registration links.': 'Neplatné prepojenia prihlášky na turnaj.',
    'Invalid category or duplicate tournament registration.': 'Neplatná kategória alebo duplicitná prihláška na turnaj.',
    'Invalid round links.': 'Neplatné prepojenia kola.',
    'Round layout or category does not belong to tournament.': 'Layout alebo kategória kola nepatrí do turnaja.',
    'Duplicate player round.': 'Duplicitné kolo hráča.',
    'Scores do not match tournament registration.': 'Výsledky nezodpovedajú prihláške na turnaj.',
    'Conflicting category or handicap within a tournament.': 'Nezhodná kategória alebo handicap v rámci turnaja.',
    'Round totals do not match hole scores.': 'Celkové výsledky kola nezodpovedajú skóre jamiek.',
    'Duplicate player and round in this file.': 'Duplicitný hráč a kolo v tomto súbore.',
    'GitHub repository and token are required together.': 'GitHub repozitár a token musia byť zadané spoločne.',
    'GitHub data file was not found. Upload your local league.json to the configured repository first.': 'Dátový súbor GitHub sa nenašiel. Najprv nahrajte lokálny league.json do nastaveného repozitára.',
    'Data changed since this page loaded. Refresh and try again.': 'Údaje sa od načítania stránky zmenili. Obnovte stránku a skúste znova.',
    'Could not reach GitHub storage. No changes were saved.': 'GitHub úložisko nie je dostupné. Žiadne zmeny sa neuložili.',
    'GitHub data file is too large for this simple store.': 'Dátový súbor GitHub je pre toto úložisko príliš veľký.',
    'Data exceeds this simple GitHub store’s 1 MB limit. Export a backup and switch storage before adding more results.': 'Údaje prekračujú limit úložiska GitHub 1 MB. Pred pridaním ďalších výsledkov exportujte zálohu a zmeňte úložisko.',
})


def translate(value, language=None):
    language = language or streamlit.session_state.get('language', 'sk')
    if not isinstance(value, str) or language == 'en':
        return value
    if value in SK:
        return SK[value]
    row_error = re.fullmatch(r'Row (\d+): (.*)', value)
    if row_error:
        return 'Riadok ' + row_error[1] + ': ' + translate(row_error[2], language)
    for prefix, localized in [('Invalid stored data: ', 'Neplatné uložené údaje: '),
                              ('Invalid backup: ', 'Neplatná záloha: '),
                              ('Could not read export: ', 'Export sa nepodarilo načítať: ')]:
        if value.startswith(prefix):
            return localized + translate(value[len(prefix):], language)
    if value.startswith('No ') and value.endswith(' available yet.'):
        return 'Zatiaľ nie sú dostupné údaje: ' + translate(value[3:-15].capitalize(), language) + '.'
    for english, slovak in SK.items():
        if value.endswith(': ' + english):
            return value[:-len(english)] + slovak
    for pattern, replacement in [
        (r'(\d+) round\(s\)', lambda m: m[1] + (' kolo' if int(m[1]) == 1 else ' kolá' if 2 <= int(m[1]) <= 4 else ' kôl')),
        (r'(\d+) tournament\(s\)', lambda m: m[1] + (' turnaj' if int(m[1]) == 1 else ' turnaje' if 2 <= int(m[1]) <= 4 else ' turnajov')),
        (r'(\d+) players with complete scores', r'\1 hráčov s dokončenými výsledkami'),
        (r'(\d+) registered players', r'\1 prihlásených hráčov'), (r'Save (\S+) scores', r'Uložiť výsledky \1'),
        (r'Hole (\d+) is listed twice\.', r'Jamka \1 je uvedená dvakrát.'),
        (r'Map a score column for hole (\d+)\.', r'Priraďte stĺpec skóre pre jamku \1.'),
        (r'Exported total par (\d+) differs from layout par (\d+) for (.+)\. Check the layout and category profile\.', r'Celkový par \1 v exporte sa líši od paru \2 layoutu pre \3. Skontrolujte layout a profil kategórie.'),
        (r'Unknown uDisc username: (.*)\. Add it to a player first\.', r'Neznáme používateľské meno uDisc: \1. Najprv ho priraďte hráčovi.'),
        (r'(.+) must be a whole number from (\d+)(?: to (\d+))?\.', lambda m: translate(m[1], language) + ' musí byť celé číslo od ' + m[2] + (' do ' + m[3] if m[3] else '') + '.'),
        (r'(.+) must be a number\.', lambda m: translate(m[1], language) + ' musí byť číslo.'),
        (r'(.+) must be finite\.', lambda m: translate(m[1], language) + ' musí byť konečné číslo.'),
        (r'Hole (\d+)', r'Jamka \1'), (r'Round (\d+)', r'Kolo \1'),
        (r'(\d+) throws', r'\1 hodov'),
        (r'GitHub storage returned HTTP (\d+)\. Check repository access and configuration\.', r'GitHub úložisko vrátilo HTTP \1. Skontrolujte prístup a nastavenia repozitára.'),
        (r'Missing or invalid (.+)\.', r'Chýbajúce alebo neplatné údaje: \1.'),
        (r'Duplicate IDs in (.+)\.', r'Duplicitné ID v údajoch: \1.'),
    ]:
        value = re.sub(pattern, replacement, value)
    return value


class LocalizedUI:
    """Localize presentation only; widget values and DataFrame keys stay stable."""
    TEXT = {'title', 'subheader', 'header', 'caption', 'write', 'info', 'warning', 'error', 'success',
            'button', 'form_submit_button', 'selectbox', 'multiselect', 'radio', 'checkbox',
            'text_input', 'text_area', 'number_input', 'file_uploader', 'expander', 'metric', 'download_button', 'markdown'}

    def __init__(self, target, can_download):
        self.target, self.can_download = target, can_download

    def __enter__(self):
        self.target.__enter__()
        return self

    def __exit__(self, *args):
        return self.target.__exit__(*args)

    def __getattr__(self, name):
        if name == 'sidebar':
            return LocalizedUI(self.target.sidebar, self.can_download)
        original = getattr(self.target, name)
        if name not in self.TEXT | {'columns', 'dataframe', 'data_editor', 'bar_chart'}:
            return original

        @wraps(original)
        def call(*args, **kwargs):
            if name == 'download_button' and not self.can_download():
                return None
            args = list(args)
            if name in self.TEXT and args and not kwargs.get('unsafe_allow_html'):
                args[0] = translate(args[0])
            for key in ['label', 'help', 'placeholder']:
                if key in kwargs:
                    kwargs[key] = translate(kwargs[key])
            if name in {'selectbox', 'multiselect', 'radio'}:
                options = list(args[1] if len(args) > 1 else kwargs.get('options', []))
                key = kwargs.get('key')
                current = streamlit.session_state.get(key) if key else None
                # Reassert the canonical value before translated widget labels/options
                # change its identity. Keep the default index stable across reruns.
                if name != 'multiselect' and current in options and key:
                    streamlit.session_state[key] = current
                elif name == 'multiselect' and isinstance(current, list) and key:
                    streamlit.session_state[key] = [value for value in current if value in options]
                formatter = kwargs.get('format_func', str)
                language = streamlit.session_state.get('language', 'sk')
                kwargs['format_func'] = lambda value: translate(formatter(value), language)
            if name in {'dataframe', 'data_editor'} and args:
                data = args[0].data if hasattr(args[0], 'data') else args[0]
                if hasattr(data, 'columns'):
                    configs = deepcopy(kwargs.get('column_config', {}))
                    for column in data.columns:
                        if column not in configs:
                            configs[column] = {'label': translate(column)}
                        elif configs[column] is not None:
                            configs[column]['label'] = translate(configs[column].get('label') or column)
                            if configs[column].get('help'):
                                configs[column]['help'] = translate(configs[column]['help'])
                    kwargs['column_config'] = configs
                if hasattr(data, 'columns') and not hasattr(args[0], 'data'):
                    local_columns = [c for c in ['Status', 'Action'] if c in data]
                    if local_columns:
                        args[0] = data.copy()
                        for column in local_columns:
                            args[0][column] = args[0][column].map(translate)
            if name == 'bar_chart' and args and hasattr(args[0], 'rename'):
                args[0] = args[0].rename(columns=translate)
                for axis in ['x', 'y']:
                    if axis in kwargs:
                        kwargs[axis] = translate(kwargs[axis])
            result = original(*args, **kwargs)
            if name == 'columns':
                return [LocalizedUI(column, self.can_download) for column in result]
            return result
        return call
