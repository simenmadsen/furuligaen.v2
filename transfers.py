from flask import render_template
import pandas as pd
import requests

def transfers():
    def checkGameweek():
        url3 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r3 = requests.get(url3)
        json = r3.json()
        gameweek_df = pd.DataFrame(json['events'])
        iscurrent = gameweek_df[['id', 'is_current']]
        currentGw = iscurrent.loc[(iscurrent.is_current == True)].iat[0, 0]
        return currentGw

    thisGw = checkGameweek()

    def getManagerName(lag):
        for i in range(len(teamsList['entry'])):
            if (teamsList['entry'][i] == int(lag)):
                return teamsList['player_name'][i]

    def getPlayerName(playerID):
        return names.at[playerID, 'web_name']

    def getPlayerPhoto(playerID):
        return names.at[playerID, 'code']

    def getPlayerTrans(teamId):
        url = 'https://fantasy.premierleague.com/api/entry/' + str(teamId) + '/transfers/'
        trans = requests.get(url).json()
        transfers = []
        navn = {
            'entry': teamId,
            'transfers': transfers
        }

        for obj in trans:
            if obj['event'] == thisGw:
                transfers.append({
                    'element_in': getPlayerName(obj['element_in']),
                    'element_out': getPlayerName(obj['element_out']),
                    'photo_in': getPlayerPhoto(obj['element_in']),
                    'photo_out': getPlayerPhoto(obj['element_out'])
                })
        if not transfers:
            return None
        else:
            return navn

    def getAllTransfers():
        transfers = []
        for teamId in teamsList['entry']:
            obj = getPlayerTrans(teamId)
            if obj != None:
                transfers.append(obj)
        return transfers

    data = getAllTransfers()

    result = render_template('transfers.html', data=data, getManagerName=getManagerName)

    return result

#hjelpefunskjoner
def getTeamList():
    try:
        url2 = 'https://fantasy.premierleague.com/api/leagues-classic/448728/standings/'
        r2 = requests.get(url2)
        json2 = r2.json()
        standings_df = pd.DataFrame(json2['standings'])
        league_df = pd.DataFrame(standings_df['results'].values.tolist())
        return league_df [['entry', 'player_name']]
    except:
        return None
teamsList = getTeamList()

def getBootstrapNames():
    url2 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    r2 = requests.get(url2)
    json2 = r2.json()
    return pd.DataFrame(json2['elements']).set_index('id')

names = getBootstrapNames()