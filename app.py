from flask import Flask, render_template
from numpy import empty
import pandas as pd
import requests
from datetime import timedelta, datetime
import time


app = Flask(__name__)
def getPlayerName(playerID):
    return names.at[playerID, 'web_name']

def getTeamList():
    try:
        url2 = 'https://fantasy.premierleague.com/api/leagues-classic/173312/standings/'
        r2 = requests.get(url2)
        json2 = r2.json()
        standings_df = pd.DataFrame(json2['standings'])
        league_df = pd.DataFrame(standings_df['results'].values.tolist())
        return league_df [['entry', 'player_name']]
    except:
        return None
def getNewEntries():
        url = 'https://fantasy.premierleague.com/api/leagues-classic/173312/standings/'
        r = requests.get(url).json()
        return r['new_entries']['results'] 

def getAvgHistoryScore(entryId):
        url = 'https://fantasy.premierleague.com/api/entry/' + str(entryId) + '/history/'
        r = requests.get(url).json()
        avg = (r['past'][-1]['rank'] + r['past'][-2]['rank'] + r['past'][-3]['rank']) / 3
        return "{:,}".format(int(avg))

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
    teamsList = getTeamList()
    #checks if FPL has started
    url = 'https://fantasy.premierleague.com/api/leagues-classic/173312/standings/'
    r = requests.get(url).json()
    if not r['standings']['results']:
        data = getNewEntries()
        result = render_template('warm_up.html', data = data, getAvgHistoryScore = getAvgHistoryScore)
        return result
    
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
        liste = [5, 9, 13, 17, 21, 25, 29, 33]
        for obj in liste:
            if gw < obj:
                return obj - 4 
        else:
            return 33     

    gws = getGwStart()

    def gwEnd ():
        gw = gws
        if gw == 33:
            return 38
        else:
            return gw + 3

    # For header i tabell
    def gwHeader():
        return str(gws) + "→" + str(gwEnd())

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
        
        if thisGw == 1:
            
            liveRound = livePlayerPoints_trans
            liveTotal = livePlayerPoints_trans
        if thisGw == 2 or 3 or 4:
            liveRound = teamPoints_df['total_points'][(thisGw - 2)] + livePlayerPoints_trans

            liveTotal = teamPoints_df['total_points'][(thisGw - 2)] + livePlayerPoints_trans

        if thisGw > 4:

            liveRound = (teamPoints_df['total_points'][(thisGw - 2)] - 
            teamPoints_df['total_points'][(gws - 2)]) + livePlayerPoints_trans

            liveTotal = teamPoints_df['total_points'][(thisGw - 2)] + livePlayerPoints_trans

        return [liveTotal, livePlayerPoints_trans, liveRound]

    def getTeamsPoints():
        tabell = []
        for team in teamsList['entry']:
            tabell.append(getGwRoundPoints(team))
        
        tabell_df = pd.DataFrame(tabell)
        ny_tabell = tabell_df.rename(columns={0: "Total", 1: "GWLive", 2: "Round"})
        return ny_tabell

    def getTabell():
        url2 = 'https://fantasy.premierleague.com/api/leagues-classic/173312/standings/'
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
    
    def getCap(playerId):
        url2 = 'https://fantasy.premierleague.com/api/entry/' + str(playerId)+ '/event/' + str(thisGw) + '/picks/'
        r2 = requests.get(url2)
        picks = r2.json()['picks']

        for pick in picks:
            if pick['is_captain']:
                return getPlayerName(pick['element'])

    def getChip(playerId):
        url2 = 'https://fantasy.premierleague.com/api/entry/' + str(playerId)+ '/event/' + str(thisGw) + '/picks/'
        r2 = requests.get(url2)
        activeChip = r2.json()
        if activeChip['active_chip'] == 'bboost':
            return 'Bench Boost'
        elif activeChip['active_chip'] == '3xc':
            return 'Triple Cap'
        elif activeChip['active_chip'] == 'freehit':
            return 'Free Hit'
        elif activeChip['active_chip'] == 'wildcard':
            return 'Wildcard'
        else:
            return ''

    def hasPlayed(playerId):
        teamId = teams.at[playerId, 'team']
        try:
            return all(allFix.at[teamId, 'finished_provisional'])
        except:
            try:
                return allFix.at[teamId, 'finished_provisional']
            except:
                return True
    
    def countFinishedPlayers(teamId):
        total = 0
        finished = 0
        picks = getAutoSubs(teamId)
        if getChip(teamId) == 'Bench Boost':
            for pick in picks['element']:
                if hasPlayed(pick):
                    finished += 1
            total = 15
        else:
            for pick in picks['element'][0:11]:
                if hasPlayed(pick):
                    finished += 1
            total = 11        
        return str(finished) + ' / ' + str(total)

    data = getTabell()
    gwHead = gwHeader()

    data = data.to_dict(orient='records')

    def formatScore(score):
        return "{:,}".format(score)
    
    result = render_template('main_page.html', data=data, gwHead = gwHead, thisGw = thisGw, getChip = getChip, getCap = getCap,
        countFinishedPlayers = countFinishedPlayers, formatScore = formatScore)
    
    return result

@app.route("/winners")
def vinnere():
    # Rundevinnere
    def getRoundWinners(roundStart, roundEnd):
        result = (any, any)
        high = 0
        for i in range (len(teamsList)):
            url = 'https://fantasy.premierleague.com/api/entry/' + str(teamsList.at[i,'entry']) + '/history/'
            teamPoints = requests.get(url).json()['current']
            if roundEnd == 4:
                if high < teamPoints[roundEnd - 1]['total_points']:
                    result = (teamPoints[roundEnd - 1]['total_points'], teamsList.at[i,'player_name'])
                    high = teamPoints[roundEnd - 1]['total_points']
            else:
                if high < (teamPoints[roundEnd - 1]['total_points'] - teamPoints[roundStart - 2]['total_points']):
                    result = (teamPoints[roundEnd - 1]['total_points'] - teamPoints[roundStart - 2]['total_points'],
                    teamsList.at[i,'player_name'])
                    high = teamPoints[roundEnd - 1]['total_points'] - teamPoints[roundStart - 2]['total_points']
        return result

    def getWinners():
        url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        events = requests.get(url).json()['events']
        nyRunde = [(1,4), (5,8), (9,12), (13,16), (17,20), (21,24), (25,28), (29,32), (33,38)]
        result = []
        i = 0
        gwIntervall = ["1 → 4", "5 → 8", "9 → 12", "13 → 16", "17 → 20",
        "21 → 24", "25 → 28", "29 → 32", "33 → 38"]
        for rndS, rndE in nyRunde:
            if events[rndE - 1]['data_checked']:
                rundevinnere = getRoundWinners(rndS, rndE)
                result.append({
                    'GW': gwIntervall[i],
                    'Vinner': rundevinnere[1],
                    'Poeng': rundevinnere[0]
                })
                i += 1
        return result

    data = getWinners()
    
    result = render_template('vinnere.html', data = data)

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
        
        spillerListeOrg['byttet_inn'] = False
        spillerListeOrg['byttet_ut'] = False
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
                    spillerListe.at[i, 'byttet_inn'] = True
                    spillerListe.at[11, 'byttet_ut'] = True
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

                        spillerListe.at[i, 'byttet_inn'] = True
                        spillerListe.at[j + 12, 'byttet_ut'] = True

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
                        spillerListe.at[i, 'byttet_inn'] = True
                        spillerListe.at[j + 12, 'byttet_ut'] = True  

                        countDef += 1
                        byttet = True
                        break

                    if countMid < minMid and innbytterPos == mids:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        spillerListe.at[i, 'byttet_inn'] = True
                        spillerListe.at[j + 12, 'byttet_ut'] = True                         
                        countMid += 1
                        byttet = True
                        break

                    if countAtt < minAtt and innbytterPos == atts:
                        spillerListe.iat[i,0], spillerListe[12:15].iat[j,0] = spillerListe[12:15].iat[j,0], spillerListe.iat[i,0]
                        spillerListe.iat[i,1] = 1
                        spillerListe.at[i, 'byttet_inn'] = True
                        spillerListe.at[j + 12, 'byttet_ut'] = True  
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

        spillerListe = spillerListe[['element', 'multiplier', 'byttet_ut', 'byttet_inn']]
        spillerListe['navn'] = navn
                    
        return spillerListe[['element', 'multiplier','navn', 'byttet_inn', 'byttet_ut', ]]

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
        for i in range(len(slim_picks[0:11])):
            tempId = slim_picks.at[i,'element']
            poeng.append((liveTotPoints.iat[tempId - 1, 1] + slim_picks.at[i, 'live_bonus'] - 
                    liveTotPoints.iat[tempId - 1, 2]) * slim_picks.at[i, 'multiplier'])
        
        for j in range(len(slim_picks[11:15])):
            tempId = slim_picks.at[j + 11,'element']
            poeng.append((liveTotPoints.iat[tempId - 1, 1] + slim_picks.at[j + 11, 'live_bonus'] - 
                    liveTotPoints.iat[tempId - 1, 2]) * 1)    

        return poeng
    
    def getTotalPoints(teamId):
        slim_picks = getAutoSubs(teamId)
        
        slim_picks['live_bonus'] = getLiveBonusList(teamId)
        
        poeng = []
        for i in range(len(slim_picks)):
            tempId = slim_picks.at[i,'element']
            poeng.append((liveTotPoints.iat[tempId - 1, 1] + slim_picks.at[i, 'live_bonus'] - 
                    liveTotPoints.iat[tempId - 1, 2]) * slim_picks.at[i, 'multiplier'])
  

        return poeng
    
    def getPlayerInfo(playerId): 
        url2 = 'https://fantasy.premierleague.com/api/event/' + str(thisGw) + '/live/'
        liveInfo = requests.get(url2).json()['elements']
        liveInfo = liveInfo[playerId-1]['explain']
        playerInfo = []
        test = []
        for stats in liveInfo:
            for stat in stats['stats']:
                playerInfo.append(stat)

        df = pd.DataFrame(playerInfo)
        visited = []
        for i in range(len(df)):
            tempIdentifier = df.at[i, 'identifier']
            if tempIdentifier not in visited and tempIdentifier != 'bonus':
                tempValue = df.loc[df['identifier'] == tempIdentifier, 'value'].sum()
                test.append({
                    'identifier' : tempIdentifier,
                    'value' : tempValue
                })
                visited.append(tempIdentifier)
        try:
            if bonuspoints.at[playerId] > 0:
                test.append({'identifier': 'bonus', 'points': bonuspoints.at[playerId], 'value': bonuspoints.at[playerId]})
        except:
            pass
        return test
    
    def getPointsAndPlayers(teamId):
        tabell = getAutoSubs(teamId)
        poeng = getLivePlayerPoints(teamId)

        tabell['points'] = poeng

        posisjon = []
        photo = []
        liveInfo = []
        for player in tabell['element']:
            posisjon.append(teams.at[player, 'element_type'])
            photo.append(names.at[player, 'code'])
            liveInfo.append(getPlayerInfo(player))

        tabell['pos'] = posisjon
        tabell['photo'] = photo
        tabell['liveInfo'] = liveInfo 

        return tabell[['navn', 'points', 'pos', 'photo', 'multiplier', 'byttet_inn', 'byttet_ut', 'liveInfo']]
    
    def hasPlayed(playerId):
        teamId = teams.at[playerId, 'team']
        try:
            return all(allFix.at[teamId, 'finished_provisional'])
        except:
            try:
                return allFix.at[teamId, 'finished_provisional']
            except:
                return True
    
    def countFinishedPlayers(teamId):
        total = 0
        finished = 0
        picks = getAutoSubs(teamId)
        if getChip(teamId) == 'Bench Boost':
            for pick in picks['element']:
                if hasPlayed(pick):
                    finished += 1
            total = 15
        else:
            for pick in picks['element'][0:11]:
                if hasPlayed(pick):
                    finished += 1
            total = 11        
        return str(finished) + ' / ' + str(total)


    data = getPointsAndPlayers(lagId)
    data = data.to_dict(orient='records')

    def getChip(playerId):
        url2 = 'https://fantasy.premierleague.com/api/entry/' + str(playerId)+ '/event/' + str(thisGw) + '/picks/'
        r2 = requests.get(url2)
        activeChip = r2.json()
        if activeChip['active_chip'] == 'bboost':
            return 'Bench Boost'
        elif activeChip['active_chip'] == '3xc':
            return 'Triple Cap'
        elif activeChip['active_chip'] == 'freehit':
            return 'Free Hit'
        elif activeChip['active_chip'] == 'wildcard':
            return 'Wildcard'
        else:
            return ''
          
    def getManagerName(lag):
        for i in range (len(teamsList['entry'])):
            if (teamsList['entry'][i] == int(lag)):
                return teamsList['player_name'][i]

    def getTransCost(teamId):
        url = 'https://fantasy.premierleague.com/api/entry/' + str(teamId) + '/history/'
        r = requests.get(url)
        json = r.json()
        teamPoints_df = pd.DataFrame(json['current'])
        return teamPoints_df['event_transfers_cost'][thisGw-1]

    def getFornavn(navn):
        for i in range (len(navn)):
            if navn[i] == " ":
                return navn[0:i]

    poeng = sum(getTotalPoints(lagId)) - getTransCost(lagId)

    manager = getFornavn(getManagerName(lagId))

    chip = getChip(lagId)

    countPlayed = countFinishedPlayers(lagId)

    result = render_template('lag.html', data = data, poeng = poeng, manager = manager, chip = chip, countPlayed = countPlayed)
    
    return result

@app.route("/transfers")
def transfers():
    def checkGameweek():
        url3 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r3 = requests.get(url3)
        json = r3.json()
        gameweek_df = pd.DataFrame(json['events'])
        iscurrent = gameweek_df[['id', 'is_current']]
        currentGw = iscurrent.loc[(iscurrent.is_current == True)].iat[0,0]
        return currentGw
    
    thisGw = checkGameweek()
    
    def getManagerName(lag):
        for i in range (len(teamsList['entry'])):
            if (teamsList['entry'][i] == int(lag)):
                return teamsList['player_name'][i]

    def getPlayerName(playerID):
        return names.at[playerID, 'web_name']
    
    def getPlayerPhoto(playerID):
        return names.at[playerID, 'code']

    def getPlayerTrans(teamId):
        url = 'https://fantasy.premierleague.com/api/entry/'+ str(teamId) +'/transfers/'
        trans = requests.get(url).json()
        transfers = []
        navn = {
            'entry': teamId, 
            'transfers':transfers
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

    result = render_template('transfers.html', data = data, getManagerName = getManagerName)

    return result

@app.route("/fixtures")
def fixtures():
    def getTeamInfo():
        url4 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r4 = requests.get(url4)
        teams = r4.json()['teams']
        return teams
    
    def checkGameweek():
        url3 = 'https://fantasy.premierleague.com/api/bootstrap-static/'
        r3 = requests.get(url3)
        json = r3.json()
        gameweek_df = pd.DataFrame(json['events'])
        iscurrent = gameweek_df[['id', 'is_current']]
        currentGw = iscurrent.loc[(iscurrent.is_current == True)].iat[0,0]
        return currentGw
    
    teams = getTeamInfo()
    thisGw = checkGameweek()

    def getTeamName(teamId):
        for team in teams:
            if team['id'] == teamId:
                return team["short_name"]
    
    def getTeamLogo(teamId):
        for team in teams:
            if team['id'] == teamId:
                return team['code']

    def getFixtures():
        url = 'https://fantasy.premierleague.com/api/fixtures/?event=' + str(thisGw)
        fixtures = requests.get(url).json()
        return fixtures;
    
    def dateAndTime(utc_datetime):
        utc_datetime = datetime.strptime(utc_datetime, "%Y-%m-%dT%H:%M:%SZ")
        now_timestamp = time.time()
        offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
        result = utc_datetime + offset
        return result.strftime('%A %H:%M')

    result = render_template('fixtures.html', fixtures = getFixtures(), getTeamName = getTeamName, getTeamLogo = getTeamLogo,
    dateAndTime = dateAndTime, thisGw = thisGw)

    return result

if __name__ == '__main__':
    app.debug = True
    app.run(host= '0.0.0.0', port = 5000)
