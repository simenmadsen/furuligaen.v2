from typing import Text
from flask import Flask, render_template
import pandas as pd
import requests
from datetime import timedelta, datetime

from requests.api import request

app = Flask(__name__)

def getTeamList():
        url2 = 'https://fantasy.premierleague.com/api/leagues-classic/627607/standings/'
        r2 = requests.get(url2)
        json2 = r2.json()
        standings_df = pd.DataFrame(json2['standings'])
        league_df = pd.DataFrame(standings_df['results'].values.tolist())
        return league_df [['entry', 'player_name']]

teamsList = getTeamList()

def getBootstrapTeams():
    url4 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    r4 = requests.get(url4)
    json = r4.json()
    gameweek_df = pd.DataFrame(json['elements'])
    teams = gameweek_df[['id', 'team', 'element_type']]
    teams.set_index('id', inplace = True)
    return teams

teams = getBootstrapTeams()

def getBootstrapNames():
    url2 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    r2 = requests.get(url2)
    json2 = r2.json()
    return pd.DataFrame(json2['elements']).set_index('id')

names = getBootstrapNames()


@app.route("/")
def index():
    def checkGameweek():
        url3 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r3 = requests.get(url3)
        json = r3.json()
        gameweek_df = pd.DataFrame(json['events'])
        iscurrent = gameweek_df[['id', 'is_current']]
        currentGw = iscurrent.loc[(iscurrent.is_current == True)].iat[0,0]
        return currentGw
    
    thisGw = checkGameweek()

    def getGwStart():
        gw = thisGw
        liste = [5, 9, 13, 17, 21, 25, 29, 33, 37]
        for obj in liste:
            if gw < obj:
                return obj - 4 
        else:
            return 37     

    gws = getGwStart()

    def gwEnd ():
        gw = gws
        if gw == 37 or gw == 38:
            return 38
        else:
            return gw + 3

    # For header i tabell
    def gwHeader():
        return "GW \n" + str(gws) + "→" + str(gwEnd())

    # Auto subs
    def getGwFixtures():
        url2 = 'https://fantasy.premierleague.com/api/fixtures/?event=' + str(thisGw)
        r2 = requests.get(url2)
        json2 = r2.json()
        fixtures_df = pd.DataFrame(json2)
        
        hfixtures = fixtures_df[['team_h', 'finished_provisional']]

        aFixtures = fixtures_df[['team_a', 'finished_provisional']]
        aFixtures.columns = ['team_h', 'finished_provisional']
        
        allFix = hfixtures.append(aFixtures)
        allFix.set_index('team_h', inplace = True)
        return allFix

    allFix = getGwFixtures()

    def getMinutesPlayed():
        url1 = 'https://fantasy.premierleague.com/api/event/' + str(thisGw) + '/live/'
        r1 = requests.get(url1)
        json1 = r1.json()
        liveElements_df = pd.DataFrame(json1['elements'])
        ids = liveElements_df['id']
        stats_df = pd.DataFrame(liveElements_df['stats'].values.tolist())
        minutes = pd.DataFrame(stats_df['minutes'])

        minutes.insert(0, 'id', ids, True)

        minutes.set_index('id', inplace = True)
        return minutes

    minutes = getMinutesPlayed()

    def didNotPlay(playerId):
        teamId = teams.at[playerId, 'team']
        try:
            return minutes.at[playerId, 'minutes'] == 0 and all(allFix.at[teamId, 'finished_provisional'])
        except:
            try:
                return minutes.at[playerId, 'minutes'] == 0 and allFix.at[teamId, 'finished_provisional']
            except:
                return True
    
    def getAutoSubs(teamId):   
        url4 = 'https://fantasy.premierleague.com/api/entry/' + str(teamId) + '/event/' + str(thisGw) + '/picks/'
        r4 = requests.get(url4)
        json4 = r4.json()
        picks_df = pd.DataFrame(json4['picks'])

        spillerListeOrg = picks_df[['element', 'multiplier', 'is_captain', 'is_vice_captain']]
        
        spillerListe = spillerListeOrg.copy()

        minDef = 3
        minMid = 2
        minAtt = 1

        countGk = 0
        countDef = 0
        countMid = 0
        countAtt = 0

        gk = 1
        defs = 2
        mids = 3
        atts = 4

        keeperbytte = spillerListe.iat[11, 0]

        for obj in spillerListe['element'][0:11]:
            starter = obj
            spillerpos = teams.at[starter, 'element_type']
            spilteIkke = didNotPlay(starter)

            if not spilteIkke:
                if spillerpos == gk:
                    countGk += 1
                if spillerpos == defs:
                    countDef += 1
                if spillerpos == mids:
                    countMid += 1
                if spillerpos == atts:
                    countAtt += 1

        for i in range(len(spillerListe[0:11])):
            if (countGk + countDef + countMid + countAtt) == 11:
                break
            
            starter = spillerListe.iat[i,0]
            spilteIkke = didNotPlay(starter)
            spillerpos = teams.at[starter, 'element_type']

            erKaptein = spillerListe.iat[i, 2]

            # sjekke kaptein
            if spilteIkke and erKaptein:
                spillerListe.loc[spillerListe['is_vice_captain'] == True, 'multiplier'] = spillerListe.iat[i, 1]
                spillerListe.iat[i, 1] = 0

            # keeperbytte
            if spillerpos == gk and spilteIkke:
                spillerListe.iat[i,1] = 0
                if not didNotPlay(keeperbytte):
                    spillerListe.iat[i, 0], spillerListe.iat[11, 0] = spillerListe.iat[11, 0], spillerListe.iat[i, 0]
                    spillerListe.iat[i,1] = 1
                    countGk += 1
                else:
                    countGk += 1
                    
            # bytte fra benken
            if spillerpos != gk and spilteIkke:
                
                spillerListe.iat[i,1] = 0
                byttet = False

                for j in range (len(spillerListe[12:15])):
                    if didNotPlay(spillerListe[12:15].iat[j,0]):
                        continue
                    
                    innbytterPos = teams.at[spillerListe[12:15].iat[j,0], 'element_type']

                    if countDef >= minDef and countMid >= minMid and countAtt >= minAtt:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0] 
                        spillerListe.iat[i,1] = 1

                        if innbytterPos == defs:
                            countDef += 1
                        if innbytterPos == mids:
                            countMid += 1
                        if innbytterPos == atts:
                            countAtt += 1
                        byttet = True
                        break           
                            
                    if countDef < minDef and innbytterPos == defs:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        countDef += 1
                        byttet = True
                        break

                    if countMid < minMid and innbytterPos == mids:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        countMid += 1
                        byttet = True
                        break

                    if countAtt < minAtt and innbytterPos == atts:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        countAtt += 1
                        byttet = True
                        break
                    
                if byttet == False:
                    if spillerpos == defs:
                        countDef += 1
                    if spillerpos == mids:
                        countMid += 1
                    if spillerpos == atts:
                        countAtt += 1
                    
        return spillerListe[0:15][['element', 'multiplier']]

    # Live bonus

    def getBonusLists():
        liste = []
        elements = pd.DataFrame()
        url = 'https://fantasy.premierleague.com/api/fixtures/?event=' + str(thisGw)
        r = requests.get(url)
        json = r.json()
        fixtures_df = pd.DataFrame(json)
        
        now = datetime.utcnow()
        for i in range (len(fixtures_df)):
            gameStart = fixtures_df.at[i, 'kickoff_time']
            gameStart = datetime.strptime(gameStart, "%Y-%m-%dT%H:%M:%SZ")
            played60 = gameStart + timedelta(minutes = 79)
            if now > played60:
                try:
                    stats_df = pd.DataFrame(fixtures_df['stats'].iloc[i])
                    stats_a = pd.DataFrame(stats_df.loc[9,'a'])
                    stats_h = pd.DataFrame(stats_df.loc[9,'h'])
                    samlet = stats_a.append(stats_h)
                    sort = samlet.sort_values(by=['value'], ascending=False)
                    ferdig = sort.reset_index(drop=True)
                    bps = ferdig[0:8].copy()
                    elements = elements.append(bps, ignore_index = True, sort = False)
                    
                    first = False
                    second = False
                    third = False
                    count = 0
                    for j in range(len(bps)):
                        if first == False:
                            try:
                                if (bps.iat[j,0] == bps.iat[j+1,0]):
                                    liste.append(3)
                                    count += 1
                                elif (bps.iat[j,0] != bps.iat[j+1,0]):
                                    liste.append(3)
                                    count += 1
                                    first = True
                            except:
                                pass

                        elif second == False and count <= 1:
                            try:
                                if (bps.iat[j,0] == bps.iat[j+1,0]):
                                    liste.append(2)
                                    count -= 1
                                elif (bps.iat[j,0] != bps.iat[j+1,0]):
                                    liste.append(2)
                                    count += 1
                                    second = True
                            except:
                                pass

                        elif third == False and count == 2:
                            try:
                                if (bps.iat[j,0] == bps.iat[j+1,0]):
                                    liste.append(1)
                                elif (bps.iat[j,0] != bps.iat[j+1,0]):
                                    liste.append(1)
                                    third = True
                            except:
                                pass
                        else:
                            liste.append(0)
                except:
                    pass
        try:
            elements['bonus'] = liste
            return elements.set_index('element', inplace=False)['bonus']
        except:
            return []

    bonuspoints = getBonusLists()

    def getLiveBonusList(teamId):
        picks = getAutoSubs(teamId)
        bonusPoeng = []
        for ids in picks['element']:
            try:
                bonusPoeng.append(sum(bonuspoints.at[ids]))
            except:
                try:
                    bonusPoeng.append(bonuspoints.at[ids])
                except:
                    bonusPoeng.append(0)
            
        return bonusPoeng


    def getAllPlayerList():
        url = 'https://fantasy.premierleague.com/api/event/' + str(thisGw) + '/live/'
        r = requests.get(url)
        json = r.json()
        liveElements_df = pd.DataFrame(json['elements'])
        liveId = liveElements_df['id']
        stats_df = pd.DataFrame(liveElements_df['stats'].values.tolist())
        liveTotPoints_df = pd.DataFrame(stats_df[['total_points', 'bonus']])
        liveTotPoints_df.insert(0,'id', liveId, True)
        return liveTotPoints_df

    liveTotPoints = getAllPlayerList()

    def getLivePlayerPoints(teamId):
        slim_picks = getAutoSubs(teamId)
        
        slim_picks['live_bonus'] = getLiveBonusList(teamId)
        
        poeng = 0
        for i in range(len(slim_picks)):
            tempId = slim_picks.iat[i,0]
            poeng += (liveTotPoints.iat[tempId - 1, 1] + slim_picks.iat[i, 2] - 
                    liveTotPoints.iat[tempId - 1, 2]) * slim_picks.iat[i, 1] 
            
        return poeng    

    def getGwRoundPoints(teamId):
        url = 'https://fantasy.premierleague.com/api/entry/' + str(teamId) + '/history/'
        r = requests.get(url)
        json = r.json()
        teamPoints_df = pd.DataFrame(json['current'])
        
        livePlayerPoints = getLivePlayerPoints(teamId) 
        
        livePlayerPoints_trans = livePlayerPoints - teamPoints_df['event_transfers_cost'][thisGw-1]
        
        try:
            liveRound = (teamPoints_df['total_points'][(thisGw - 2)] - 
            teamPoints_df['total_points'][(gws - 2)]) + livePlayerPoints_trans

            liveTotal = teamPoints_df['total_points'][(thisGw - 2)] + livePlayerPoints_trans
        except:
            liveRound = 0
            liveTotal = 0

        return [liveTotal, livePlayerPoints_trans, liveRound]

    def getTeamsPoints():
        tabell = []
        for team in teamsList['entry']:
            tabell.append(getGwRoundPoints(team))
        
        tabell_df = pd.DataFrame(tabell)
        ny_tabell = tabell_df.rename(columns={0: "Total", 1: "GWLive", 2: "Round"})
        return ny_tabell

    def getTabell():
        url2 = 'https://fantasy.premierleague.com/api/leagues-classic/627607/standings/'
        r2 = requests.get(url2)
        json2 = r2.json()
        standings_df = pd.DataFrame(json2['standings'])
        league_df = pd.DataFrame(standings_df['results'].values.tolist())

        tabell = getTeamsPoints()
        
        tabell.insert(0, 'Navn', league_df[['player_name']], True)
        tabell['entry'] = teamsList['entry']
        tabellSort = tabell.sort_values ('Round', ascending=False)
        tabellSort.insert(0, "#", range(1, len(tabell) + 1), True)
        tabellSort.columns = ['Rank', 'Navn', 'Tot', 'GW', 'GWround', 'Entry']
        
        return tabellSort
    
    gwHead = gwHeader()

    data = getTabell()
    data = data.apply(pd.Series.explode).to_dict(orient='records')
    result = render_template('main_page.html', data=data, gwHead = gwHead, thisGw = thisGw)
    
    return result


@app.route("/vinnere")
def vinnere():
    def checkGameweek():
        url3 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r3 = requests.get(url3)
        json = r3.json()
        gameweek_df = pd.DataFrame(json['events'])
        iscurrent = gameweek_df[['id', 'is_current']]
        currentGw = iscurrent.loc[(iscurrent.is_current == True)].iat[0,0]
        return currentGw

    thisGw = checkGameweek()

    def getGwStart():
        gw = thisGw
        liste = [5, 9, 13, 17, 21, 25, 29, 33, 37]
        for obj in liste:
            if gw < obj:
                return obj - 4 
        else:
            return 37     

    gws = getGwStart()

    # Rundevinnere
    def getRoundPoints(slutter):
        starter = slutter - 5
        slutter = starter + 4

        result = []
        navn = []
        # Finner scoren til alle spillerne i parmeterintervallet
        
        for i in range (len(teamsList)):
            url = 'https://fantasy.premierleague.com/api/entry/' + str(teamsList.iat[i,0]) + '/history/'
            r = requests.get(url)
            json = r.json()
            teamPoints_df = pd.DataFrame(json['current'])
            result.append(teamPoints_df['points'][starter:slutter].sum() - 
                        teamPoints_df['event_transfers_cost'][starter:slutter].sum())
            navn.append(teamsList.iat[i,1])
        
        samlet = pd.DataFrame(result, navn)
        samlet.reset_index(inplace = True)
        maxClm = samlet.loc[samlet[0].argmax()]
        
        return maxClm

    def getWinners():
        nyRunde = [5, 9, 13, 17, 21, 25, 29, 33, 37]
        rundevinnere = []
        gwIntervall = ["1 → 4", "5 → 8", "9 → 12", "13 → 16", "17 → 20",
        "21 → 24", "25 → 28", "29 → 32", "33 → 36", "37 → 38"]
        for obj in nyRunde:
            if gws < obj:
                break
            if gws >= obj:
                rundevinnere.append(getRoundPoints(obj))
                
        result = pd.DataFrame(rundevinnere)
        result.insert(0, 'Runde', gwIntervall[:(len(result))], True)
        result.columns = ['GW', 'Vinner', 'Poeng']
        return result
    
    result = render_template('vinnere.html', tables=[getWinners().to_html(classes="table table-dark table-borderless table-striped", border=0)])

    return result

@app.route("/<lagId>")
def lag(lagId):
    def checkGameweek():
        url3 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r3 = requests.get(url3)
        json = r3.json()
        gameweek_df = pd.DataFrame(json['events'])
        iscurrent = gameweek_df[['id', 'is_current']]
        currentGw = iscurrent.loc[(iscurrent.is_current == True)].iat[0,0]
        return currentGw

    thisGw = checkGameweek()

    def getGwFixtures():
        url2 = 'https://fantasy.premierleague.com/api/fixtures/?event=' + str(thisGw)
        r2 = requests.get(url2)
        json2 = r2.json()
        fixtures_df = pd.DataFrame(json2)
        
        hfixtures = fixtures_df[['team_h', 'finished_provisional']]

        aFixtures = fixtures_df[['team_a', 'finished_provisional']]
        aFixtures.columns = ['team_h', 'finished_provisional']
        
        allFix = hfixtures.append(aFixtures)
        allFix.set_index('team_h', inplace = True)
        return allFix

    allFix = getGwFixtures()

    def getMinutesPlayed():
        url1 = 'https://fantasy.premierleague.com/api/event/' + str(thisGw) + '/live/'
        r1 = requests.get(url1)
        json1 = r1.json()
        liveElements_df = pd.DataFrame(json1['elements'])
        ids = liveElements_df['id']
        stats_df = pd.DataFrame(liveElements_df['stats'].values.tolist())
        minutes = pd.DataFrame(stats_df['minutes'])

        minutes.insert(0, 'id', ids, True)

        minutes.set_index('id', inplace = True)
        return minutes

    minutes = getMinutesPlayed()

    def getPlayerName(playerID):
        return names.at[playerID, 'web_name']

    def didNotPlay(playerId):
        teamId = teams.at[playerId, 'team']
        try:
            return minutes.at[playerId, 'minutes'] == 0 and all(allFix.at[teamId, 'finished_provisional'])
        except:
            try:
                return minutes.at[playerId, 'minutes'] == 0 and allFix.at[teamId, 'finished_provisional']
            except:
                return True
    
    def getAutoSubs(teamId):   
        url4 = 'https://fantasy.premierleague.com/api/entry/' + str(teamId) + '/event/' + str(thisGw) + '/picks/'
        r4 = requests.get(url4)
        json4 = r4.json()
        picks_df = pd.DataFrame(json4['picks'])

        spillerListeOrg = picks_df[['element', 'multiplier', 'is_captain', 'is_vice_captain']]
        
        spillerListe = spillerListeOrg.copy()

        minDef = 3
        minMid = 2
        minAtt = 1

        countGk = 0
        countDef = 0
        countMid = 0
        countAtt = 0

        gk = 1
        defs = 2
        mids = 3
        atts = 4

        keeperbytte = spillerListe.iat[11, 0]

        for obj in spillerListe['element'][0:11]:
            starter = obj
            spillerpos = teams.at[starter, 'element_type']
            spilteIkke = didNotPlay(starter)

            if not spilteIkke:
                if spillerpos == gk:
                    countGk += 1
                if spillerpos == defs:
                    countDef += 1
                if spillerpos == mids:
                    countMid += 1
                if spillerpos == atts:
                    countAtt += 1

        for i in range(len(spillerListe[0:11])):
            if (countGk + countDef + countMid + countAtt) == 11:
                break
            
            starter = spillerListe.iat[i,0]
            spilteIkke = didNotPlay(starter)
            spillerpos = teams.at[starter, 'element_type']

            erKaptein = spillerListe.iat[i, 2]

            # sjekke kaptein
            if spilteIkke and erKaptein:
                spillerListe.loc[spillerListe['is_vice_captain'] == True, 'multiplier'] = spillerListe.iat[i, 1]
                spillerListe.iat[i, 1] = 0

            # keeperbytte
            if spillerpos == gk and spilteIkke:
                spillerListe.iat[i,1] = 0
                if not didNotPlay(keeperbytte):
                    spillerListe.iat[i, 0], spillerListe.iat[11, 0] = spillerListe.iat[11, 0], spillerListe.iat[i, 0]
                    spillerListe.iat[i,1] = 1
                    countGk += 1
                else:
                    countGk += 1
                    
            # bytte fra benken
            if spillerpos != gk and spilteIkke:
                
                spillerListe.iat[i,1] = 0
                byttet = False

                for j in range (len(spillerListe[12:15])):
                    if didNotPlay(spillerListe[12:15].iat[j,0]):
                        continue
                    
                    innbytterPos = teams.at[spillerListe[12:15].iat[j,0], 'element_type']

                    if countDef >= minDef and countMid >= minMid and countAtt >= minAtt:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0] 
                        spillerListe.iat[i,1] = 1

                        if innbytterPos == defs:
                            countDef += 1
                        if innbytterPos == mids:
                            countMid += 1
                        if innbytterPos == atts:
                            countAtt += 1
                        byttet = True
                        break           
                            
                    if countDef < minDef and innbytterPos == defs:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        countDef += 1
                        byttet = True
                        break

                    if countMid < minMid and innbytterPos == mids:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        countMid += 1
                        byttet = True
                        break

                    if countAtt < minAtt and innbytterPos == atts:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        countAtt += 1
                        byttet = True
                        break
                    
                if byttet == False:
                    if spillerpos == defs:
                        countDef += 1
                    if spillerpos == mids:
                        countMid += 1
                    if spillerpos == atts:
                        countAtt += 1

        navn = []
        for spiller in spillerListe['element']:
            navn.append(getPlayerName(spiller))

        spillerListe = spillerListe[0:15][['element', 'multiplier']]
        spillerListe['navn'] = navn
        
        return spillerListe

    def getBonusLists():
        liste = []
        elements = pd.DataFrame()
        url = 'https://fantasy.premierleague.com/api/fixtures/?event=' + str(thisGw)
        r = requests.get(url)
        json = r.json()
        fixtures_df = pd.DataFrame(json)
        
        now = datetime.utcnow()
        for i in range (len(fixtures_df)):
            gameStart = fixtures_df.at[i, 'kickoff_time']
            gameStart = datetime.strptime(gameStart, "%Y-%m-%dT%H:%M:%SZ")
            played60 = gameStart + timedelta(minutes = 79)
            if now > played60:
                try:
                    stats_df = pd.DataFrame(fixtures_df['stats'].iloc[i])
                    stats_a = pd.DataFrame(stats_df.loc[9,'a'])
                    stats_h = pd.DataFrame(stats_df.loc[9,'h'])
                    samlet = stats_a.append(stats_h)
                    sort = samlet.sort_values(by=['value'], ascending=False)
                    ferdig = sort.reset_index(drop=True)
                    bps = ferdig[0:8].copy()
                    elements = elements.append(bps, ignore_index = True, sort = False)
                    
                    first = False
                    second = False
                    third = False
                    count = 0
                    for j in range(len(bps)):
                        if first == False:
                            try:
                                if (bps.iat[j,0] == bps.iat[j+1,0]):
                                    liste.append(3)
                                    count += 1
                                elif (bps.iat[j,0] != bps.iat[j+1,0]):
                                    liste.append(3)
                                    count += 1
                                    first = True
                            except:
                                pass

                        elif second == False and count <= 1:
                            try:
                                if (bps.iat[j,0] == bps.iat[j+1,0]):
                                    liste.append(2)
                                    count -= 1
                                elif (bps.iat[j,0] != bps.iat[j+1,0]):
                                    liste.append(2)
                                    count += 1
                                    second = True
                            except:
                                pass

                        elif third == False and count == 2:
                            try:
                                if (bps.iat[j,0] == bps.iat[j+1,0]):
                                    liste.append(1)
                                elif (bps.iat[j,0] != bps.iat[j+1,0]):
                                    liste.append(1)
                                    third = True
                            except:
                                pass
                        else:
                            liste.append(0)
                except:
                    pass
        try:
            elements['bonus'] = liste
            return elements.set_index('element', inplace=False)['bonus']
        except:
            return []

    bonuspoints = getBonusLists()

    def getLiveBonusList(teamId):
        picks = getAutoSubs(teamId)
        bonusPoeng = []
        for ids in picks['element']:
            try:
                bonusPoeng.append(sum(bonuspoints.at[ids]))
            except:
                try:
                    bonusPoeng.append(bonuspoints.at[ids])
                except:
                    bonusPoeng.append(0)
            
        return bonusPoeng

    def getAllPlayerList():
        url = 'https://fantasy.premierleague.com/api/event/' + str(thisGw) + '/live/'
        r = requests.get(url)
        json = r.json()
        liveElements_df = pd.DataFrame(json['elements'])
        liveId = liveElements_df['id']
        stats_df = pd.DataFrame(liveElements_df['stats'].values.tolist())
        liveTotPoints_df = pd.DataFrame(stats_df[['total_points', 'bonus']])
        liveTotPoints_df.insert(0,'id', liveId, True)
        return liveTotPoints_df

    liveTotPoints = getAllPlayerList()

    def getLivePlayerPoints(teamId):
        slim_picks = getAutoSubs(teamId)
        
        slim_picks['live_bonus'] = getLiveBonusList(teamId)
        
        poeng = []
        for i in range(len(slim_picks)):
            tempId = slim_picks.at[i,'element']
            poeng.append((liveTotPoints.iat[tempId - 1, 1] + slim_picks.at[i, 'live_bonus'] - 
                    liveTotPoints.iat[tempId - 1, 2]) * slim_picks.at[i, 'multiplier'])
            
        return poeng

    def getPointsAndPlayers(teamId):
        tabell = getAutoSubs(teamId)
        poeng = getLivePlayerPoints(teamId)

        tabell['points'] = poeng

        posisjon = []
        photo = []
        for player in tabell['element']:
            posisjon.append(teams.at[player, 'element_type'])
            photo.append(names.at[player, 'code'])

        tabell['pos'] = posisjon
        tabell['photo'] = photo
        return tabell[['navn', 'points', 'pos', 'photo']]
    

    data = getPointsAndPlayers(lagId)
    data = data.apply(pd.Series.explode).to_dict(orient='records')

    gk = []
    defs = []
    mid = []
    att = []

    gk_photo = []
    defs_photo = []
    mid_photo = []
    att_photo = []

    benk = []
    benk_photo = []

    for i in range (len(data[11:15])):
        benk.append(data[i+11]['navn'] + "(" + str(data[i+11]['points']) + ")")
        benk_photo.append(data[i+11]['photo'])
    for i in range (len(data[0:11])):
        if (data[i]['pos'] == 1):
            gk_photo.append(data[i]['photo'])
            gk.append(data[i]['navn'] + "(" + str(data[i]['points']) + ")")
        if (data[i]['pos'] == 2):
            defs_photo.append(data[i]['photo'])
            defs.append(data[i]['navn'] + "(" + str(data[i]['points']) + ")")
        if (data[i]['pos'] == 3):
            mid_photo.append(data[i]['photo'])
            mid.append(data[i]['navn'] + "(" + str(data[i]['points']) + ")")
        if (data[i]['pos'] == 4):
            att_photo.append(data[i]['photo'])
            att.append(data[i]['navn'] + "(" + str(data[i]['points']) + ")")
            

    result = render_template('lag.html', gk = gk, defs = defs, mid = mid, att = att, 
    gk_photo = gk_photo, defs_photo = defs_photo, mid_photo = mid_photo, att_photo = att_photo,
    benk = benk, benk_photo = benk_photo)
    
    return result

if __name__ == '__main__':
    app.debug = True
    app.run(host= '0.0.0.0', port = 5000)