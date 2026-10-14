"""Presentation search only: stored names/usernames are never rewritten."""
import unicodedata


def search_key(text):
    decomposed = unicodedata.normalize('NFKD', str(text).casefold())
    return ' '.join(''.join(c for c in decomposed if not unicodedata.combining(c)).split())


def matching_players(players, query, include_username=False):
    words = search_key(query).split()
    def matches(player):
        label = player['first_name'] + ' ' + player['last_name']
        if include_username:
            label += ' ' + player.get('udisc', '')
        key = search_key(label)
        return all(word in key for word in words)
    return [player for player in players if matches(player)]
