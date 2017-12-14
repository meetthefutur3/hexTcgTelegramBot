# -*- coding: utf-8 -*-


import mongoengine as db
from wrappers import *

import random
import uuid
import json

import time

GAME_WINNER = {1:'GameOneWinner', 2:'GameTwoWinner', 3:'GameThreeWinner'}

db.connect(host='localhost', port=27017, db='HEXREM')
'''
    @property
    def t1(self):
        won, played = 0, 0
        for opp in self.opponents:
            won += opp.matches_won
            played += opp.matches_played
        if played:
            return 100.0*won/played
        else:
            return 100.0

    @property
    def t2(self):
        won, played = 0, 0
        for opp in self.opponents:
            for opp_opp in opp.opponents:
                won += opp_opp.matches_won
                played += opp_opp.matches_played
        if played:
            return 100.0*won/played
        else:
            return 100.0
'''

def _sort(p):
    return (-p.matches_won, -p.t1, -p.t2, -p.t3)

def _sort_t1(p):
    return (-p.matches_won, -p.t1)

@db_auto_update_modification_time
class Player(db.Document):

    meta = dict(
        collection="tournament__player",
        )

    t_uid = db.StringField(default='')
    nickname = db.StringField(default='')
    matches_won = db.IntField(default=0)
    matches_played = db.IntField(default=0)
    games_won = db.IntField(default=0)
    games_played = db.IntField(default=0)
    byes = db.IntField(default=0)
    opponents = db.ListField(db.ReferenceField('self'), default=list)
#    dropped = db.IntField(default=0) # номер раунда, в котором дропнулись

    created = db.DateTimeField(default=None)
    modified = db.DateTimeField(default=None)


    def __init__(self, *args, **kwargs):
        super(Player, self).__init__(*args, **kwargs)
        self.save()

    @property
    def t1(self):
        sum_wr, n = 0, 0
        for opp in self.opponents:
            sum_wr += max(1/3, (opp.matches_won-opp.byes)/((opp.matches_played-opp.byes) or 1))
            n += 1
        return 100.0*sum_wr/(n or 1)

    @property
    def t2(self):
        sum_wr, n, u_opp_opp = 0, 0, []
        for opp in self.opponents:
            for opp2 in opp.opponents:
                if opp2 != self: # and opp2 not in u_opp_opp:
                    u_opp_opp.append(opp2)
        for opp in u_opp_opp:
            sum_wr += max(1/3, (opp.matches_won-opp.byes)/((opp.matches_played-opp.byes) or 1))
            n += 1
        return 100.0*sum_wr/(n or 1)

    @property
    def t3(self):
        return 100.0*self.games_won/(self.games_played or 1)

    @property
    def info(self):
        return ('{:>15} {}/{}'+' {:6.2f}'*3).format(self.nickname, self.matches_won, self.matches_played, self.t1, self.t2, self.t3)

@db_auto_update_modification_time
class Match(db.Document):

    meta = dict(
        collection="tournament__match",
        )

    uid = db.StringField(default='')
    t_uid = db.StringField(default='')
    is_bye = db.BooleanField(default=False)
    players = db.ListField(db.ReferenceField(Player), default=list)
    results = db.ListField(db.ReferenceField(Player), default=list)
    is_finished = db.BooleanField(default=False)
    i_round = db.IntField(default=0)

    created = db.DateTimeField(default=None)
    modified = db.DateTimeField(default=None)


    def __init__(self, *args, **kwargs):
        super(Match, self).__init__(*args, **kwargs)
#        self.t_uid = t_uid
#        self.uid = kwargs['uid']
#        self.players = kwargs['players']
        #self.players = list(kwargs['PlayerOne'], kwargs['PlayerOne'])
        self.save()

    def update_match(self, *args, **kwargs): # вернем 1 - матч закончен

        if self.players[0]==self.players[1]:
            self.is_bye = True
            self.is_finished = True
        else:
            for gw in range(1,4): # муть на будущее
                if kwargs[GAME_WINNER[gw]]:
                    if len(self.results) < gw:
                        self.results.append(Player.objects(nickname=kwargs[GAME_WINNER[gw]], t_uid=self.t_uid).first())
                else:
                    break

            if len(self.results) == 2 and self.results[0] == self.results[1]:
                self.is_finished = True
            if len(self.results) == 3:
                self.is_finished = True

        self.i_round = self.players[0].matches_played

        self.save()
        if self.is_finished:
            self.finalize_match()
            return 1

        return 0

    def finalize_match(self):
        if self.is_bye:
            self.players[0].matches_played += 1
            self.players[0].matches_won += 1
            self.players[0].byes += 1
#            self.players[0].opponents.append(self.players[0])
            self.players[0].save()
            return
        for p in self.players:
            p.matches_played += 1
            p.matches_won += 1 if p == self.results[-1] else 0
            p.games_played += len(self.results)
            p.games_won += self.results.count(p)
            p.opponents.append(self.players[1^self.players.index(p)])
            p.save()


@db_auto_update_modification_time
class Tournament(db.Document):

    meta = dict(
        collection="tournament",
        )

    uid = db.StringField(default='')
    finished_matches = db.ListField(db.IntField(), default=list)
    players = db.DictField(db.DynamicField, default=None)
    n_players = db.IntField(default=0)
    n_rounds = db.IntField(default=0)

    created = db.DateTimeField(default=None)
    modified = db.DateTimeField(default=None)


    def __init__(self, *args, **kwargs):
        super(Tournament, self).__init__(*args, **kwargs)

    def create_standings(self, msg):
        self.uid = msg['ID']
        self.finished_matches = []
        self.players = {p['Name']:Player(nickname=p['Name'], t_uid=self.uid) for p in msg['Players']}
        self.n_players = len(self.players)
        self.n_rounds = len(bin(self.n_players-1))-2
        self.update_standings(msg=msg)
        self.save()

    def get_standings(self):
        return sorted(self.players.values(), key=_sort)

    def get_simulated_top(self): #  only 1st tiebreaker matters
        return sorted(self.players.values(), key=_sort_t1)[:self.sim_top]

    def update_standings(self, msg):
        for g in msg['Games']: #[self.last_match_index:]:
#        for g in msg['Games'][self.i_matches[self.current_round-1 if self.current_round else 0]:self.i_matches[self.current_round]]: #[self.last_match_index:]:
            if g['ID'] in self.finished_matches:
                continue
            if self.find_match(**g).update_match(**g):
                self.finished_matches.append(g['ID'])
             #   print ('match {} has been finished.'.format(g['ID']))
        self.save()
#        self.check_current_round(msg)

#    def check_current_round(self, msg):
#        if len(msg['Games']) > self.i_matches[self.current_round]:
#            self.current_round += 1
#            self.i_matches.append(len(msg['Games']))
#        self.save()



# рекурсивно пробегаем по всем незавершенным каткам, собираем инфу, и тд. НЕ ЗАБЫТЬ ПРО РЕЛОАД турнир инстанса, иначе приедем.
    def get_possible_standings(self, top=8):
        self.simulated_results = {p:0 for p in self.players}
        self.sim_top = top
        self.sim_index = 0
        self.start_sim_time = time.time()
        still_playing_pairs = [[p.nickname for p in m.players] for m in Match.objects(is_finished=False)]
        self.simulate_match(still_playing_pairs)
        print('Probabilities for placing in top {}:'.format(self.sim_top))
        for p in self.simulated_results:
            if self.simulated_results[p]:
                print('{:>20} - {:6.2f}'.format(p, self.simulated_results[p]/self.sim_index))
        self.reload()

    def simulate_match(self, pairs):
        if pairs:
            self.players[pairs[0][0]].matches_played += 1
            self.players[pairs[0][1]].matches_played += 1
            self.players[pairs[0][0]].matches_won += 1
            self.simulate_match(pairs[1:])
            self.players[pairs[0][0]].matches_won -= 1
            self.players[pairs[0][1]].matches_won += 1
            self.simulate_match(pairs[1:])
        else:
            self.sim_index += 1
            if not self.sim_index % 100:
                print('Simulation lasts {:4.0f} seconds. Simulated outcomes: {}.'.format(time.time()-self.start_sim_time, self.sim_index))
            for p in self.get_simulated_top():
                self.simulated_results[p.nickname] += 1


    def st(self):
        i = 0
        st = []
        for p in self.get_standings():
            i+=1
            st.append('{:3}. {}'.format(i, p.info))
        return st

    def find_match(self, *args, **kwargs):
        return Match.objects(uid=kwargs['ID'], t_uid=self.uid).first() if Match.objects(uid=kwargs['ID'], t_uid=self.uid) else Match(uid=kwargs['ID'], players=[self.players[p] for p in (kwargs['PlayerOne'], kwargs['PlayerTwo'])], t_uid=self.uid)

    def delete(self):
        Player.objects(t_uid=self.uid).delete()
        Match.objects(t_uid=self.uid).delete()
        super(Tournament, self).delete()

'''
from data import *

start_msg = json.loads(TEST_MSG)['TournamentData']
random_msgs = [json.loads(msg)['TournamentData'] for msg in [MSG1, MSG2, MSG3]]

turik = Tournament(start_msg)
'''

class Apilog(db.DynamicDocument):
    meta = {'collection':'tournament_data'}

def get_m(t_uid='1117785859'):
    msg = Apilog.objects(Message='Tournament',TournamentData__ID=t_uid,TournamentData__Games__ne=[],User__in=['Shinshire','Eaglov']).order_by('-_id')[0].TournamentData
    tour = Tournament()
    tour.create_standings(msg)
    return tour

def get_t(t_uid='1117785859'):

    try:
        print('Looking for tournament #{} in database...'.format(t_uid))
        return Tournament.objects.get(uid=t_uid)
    except db.DoesNotExist:
        print('Tournament #{} wasn\'t found, creating...'.format(t_uid))
        return get_m(t_uid)

def get_info(tournamentid):

    msg = Apilog.objects(Message='Tournament',TournamentData__Games__ne=[],_id=tournamentid).order_by('-_id')[0].TournamentData
    tour = Tournament()
    tour.create_standings(msg)
    s = tour.st()
    tour.delete()
    return s
