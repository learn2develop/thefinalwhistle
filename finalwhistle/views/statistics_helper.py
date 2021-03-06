# -*- coding: utf-8 -*-
import json
from finalwhistle.apis import fd_api
from finalwhistle.models.football import *
from sqlalchemy import or_, desc, func, asc
from flask import request
from finalwhistle import db
from finalwhistle.views.data_views_helper import get_player_image, get_player_information

# CONSTANTS #####################################################################


ROOT = 'finalwhistle/'

PLAYER_IMAGES = ROOT + 'cache/players_images.json'
CLUB_CRESTS = ROOT + 'cache/club_crests.json'


# FUNCTIONS #####################################################################

def get_player_comparison():

    # No POST request
    if len(request.args) == 0:
        return dict(team1=None, team2=None, error=None)

    invalid = False

    try:
        player1 = int(request.args.get('p1'))
        player2 = int(request.args.get('p2'))
    except ValueError:
        invalid = True
    except TypeError:
        invalid = True

    if invalid:
        return dict(team1=None, team2=None, error='Two players required, please select two players')

    # In case data is submitted manually check if teams exist
    selected_player1 = Player.query.filter_by(player_id=player1)
    selected_player2 = Player.query.filter_by(player_id=player2)

    if selected_player1 is None or selected_player2 is None or player1 == player2:
        return dict(team1=None, team2=None, error='Invalid combination of clubs, please choose different clubs')

    return dict(
        player1=get_player_information(player1),
        player2=get_player_information(player2),
        error=''
    )


def get_team_comparison():
    """
    Compare two team together based on goals, cards, won games, lost games, etc.
    :return:
    """
    invalid = False

    # No POST request
    if len(request.args) == 0:
        return dict(team1=None, team2=None, error=None)

    try:
        team1 = int(request.args.get('team1'))
        team2 = int(request.args.get('team2'))
    except ValueError:
        invalid = True
    except TypeError:
        invalid = True

    if invalid:
        return dict(team1=None, team2=None, error='2 clubs required, please select 2 clubs')

    # In case data is submitted manually check if teams exist
    selected_team1 = Team.query.filter_by(team_id=team1)
    selected_team2 = Team.query.filter_by(team_id=team2)

    if selected_team1 is None or selected_team2 is None or team1 == team2:
        return dict(team1=None, team2=None, error='Invalid combination of clubs, please choose different clubs')

    return dict(
        team1=fetch_team_statistics(team1),
        team2=fetch_team_statistics(team2),
        common=get_common_matches(team1, team2),
        error=''
    )


def fetch_team_statistics(id):
    """
    Fetch statistics for team
    :param id: team database id
    :return: dict
    """

    team_stats = {}

    # Team name
    team = Team.query.filter_by(team_id=id).first()
    team_stats['name'] = team.name

    # Team Crest
    source = '/v1/teams/{}'.format(team.api_id)
    fd_team = fd_api.fetch_api_data(source, 2000)
    team_stats['crest'] = fd_team['crestUrl']

    # Count all games played
    home_matches = db.session.query(db.func.count(MatchStatistics.stat_id).label('count')) \
        .filter(MatchStatistics.home_team == id) \
        .group_by(MatchStatistics.home_team).all()[0]

    away_matches = db.session.query(db.func.count(MatchStatistics.stat_id).label('count')) \
        .filter(MatchStatistics.away_team == id) \
        .group_by(MatchStatistics.away_team).all()[0]

    team_stats['matches_away'] = away_matches.count
    team_stats['matches_home'] = home_matches.count
    team_stats['matches_total'] = home_matches.count + away_matches.count

    # Home Statistic Summary
    statistic_home = db.session.query(
        db.func.sum(MatchStatistics.home_ft_goals).label('goals'),
        db.func.sum(MatchStatistics.home_shots).label('shots'),
        db.func.sum(MatchStatistics.home_shots_on_target).label('shots_on_target'),
        db.func.sum(MatchStatistics.home_corners).label('corners'),
        db.func.sum(MatchStatistics.home_fouls).label('fouls'),
        db.func.sum(MatchStatistics.home_yellow_cards).label('yellow_cards'),
        db.func.sum(MatchStatistics.home_red_cards).label('red_cards')
    ).filter(MatchStatistics.home_team == id).group_by(MatchStatistics.home_team).all()[0]

    team_stats['home'] = {
        'goals': statistic_home.goals,
        'shots': statistic_home.shots,
        'shots_on_target': statistic_home.shots_on_target,
        'corners': statistic_home.corners,
        'fouls': statistic_home.fouls,
        'yellow_cards': statistic_home.yellow_cards,
        'red_cards': statistic_home.red_cards,
    }

    # Away Statistic Summary
    statistic_away = db.session.query(
        db.func.sum(MatchStatistics.away_ft_goals).label('goals'),
        db.func.sum(MatchStatistics.away_shots).label('shots'),
        db.func.sum(MatchStatistics.away_shots_on_target).label('shots_on_target'),
        db.func.sum(MatchStatistics.away_corners).label('corners'),
        db.func.sum(MatchStatistics.away_fouls).label('fouls'),
        db.func.sum(MatchStatistics.away_yellow_cards).label('yellow_cards'),
        db.func.sum(MatchStatistics.away_red_cards).label('red_cards')
    ).filter(MatchStatistics.away_team == id).group_by(MatchStatistics.away_team).all()[0]

    team_stats['away'] = {
        'goals': statistic_away.goals,
        'shots': statistic_away.shots,
        'shots_on_target': statistic_away.shots_on_target,
        'corners': statistic_away.corners,
        'fouls': statistic_away.fouls,
        'yellow_cards': statistic_away.yellow_cards,
        'red_cards': statistic_away.red_cards,
    }

    # Total Statistic Summary
    team_stats['total'] = {
        'goals': statistic_away.goals + statistic_home.goals,
        'shots': statistic_away.shots + statistic_home.shots,
        'shots_on_target': statistic_away.shots_on_target + statistic_home.shots_on_target,
        'corners': statistic_away.corners + statistic_home.corners,
        'fouls': statistic_away.fouls + statistic_home.fouls,
        'yellow_cards': statistic_away.yellow_cards + statistic_home.yellow_cards,
        'red_cards': statistic_away.red_cards + statistic_home.red_cards,
    }

    return team_stats


def get_common_matches(team1, team2):
    """
    List all common matches between two teams
    :param team1: team 1
    :param team2: team 2
    :return: list of matches
    """

    with open(CLUB_CRESTS) as jsonfile:
        club_crest = json.load(jsonfile)

    list_of_matches = []

    matches = Match.query.join(MatchStatistics, Match.match_id == MatchStatistics.match) \
        .add_columns(Match.match_id,
                     Match.home_team,
                     Match.away_team,
                     Match.kickoff,
                     MatchStatistics.home_ft_goals,
                     MatchStatistics.away_ft_goals).order_by(desc(Match.kickoff)).all()

    for match in matches:

        if (match.home_team == team1 or match.home_team == team2) \
                and (match.away_team == team1 or match.away_team == team2):
            match_details = {}
            home_team = Team.query.filter_by(team_id=match.home_team).first()
            away_team = Team.query.filter_by(team_id=match.away_team).first()

            match_details['home_crest'] = club_crest[str(home_team.team_id)]
            match_details['away_crest'] = club_crest[str(away_team.team_id)]

            match_details['match_id'] = match.match_id
            match_details['home_team'] = home_team.name
            match_details['away_team'] = away_team.name
            match_details['home_goals'] = match.home_ft_goals
            match_details['away_goals'] = match.away_ft_goals
            match_details['kickoff_time'] = match.kickoff.strftime("%H:%M")
            match_details['kickoff_date'] = match.kickoff.strftime("%d %B %Y")
            list_of_matches.append(match_details)

    return list_of_matches


def top_tens_statistic():

    top_ten = {
        'goal_scorers': top_ten_scorers(),
        'yellow_cards': top_ten_cards(),
        'red_cards': top_ten_cards(yellow=False),
        'assistants': top_ten_assists()
    }

    return top_ten


def top_ten_scorers():
    # Away Statistic Summary
    scorers = db.session.query(
        Goal.player,
        db.func.count(Goal.player).label('goals'),
    ).group_by(Goal.player).order_by(db.func.count(Goal.player).desc()).all()

    top_scorers = []
    count = 1
    for scorer in scorers:

        player = Player.query.filter_by(player_id=scorer.player).first()

        top_scorers.append(
            dict(
                image=get_player_image(player.name, small=True),
                player=player.name,
                goals=scorer.goals,
                id=player.player_id
            )
        )

        if count == 10:
            break
        count += 1

    return top_scorers


def top_ten_assists():
    # Away Statistic Summary
    scorers = db.session.query(
        Goal.assist_player,
        db.func.count(Goal.assist_player).label('assists'),
    ).group_by(Goal.assist_player).order_by(db.func.count(Goal.assist_player).desc()).all()

    top_scorers = []
    count = 1
    for scorer in scorers:

        player = Player.query.filter_by(player_id=scorer.assist_player).first()

        top_scorers.append(
            dict(
                image=get_player_image(player.name, small=True),
                player=player.name,
                goals=scorer.assists,
                id=player.player_id
            )
        )

        if count == 10:
            break
        count += 1

    return top_scorers


def top_ten_cards(yellow=True):
    # Away Statistic Summary
    statistics = db.session.query(
        Card.player,
        db.func.count(Card.player).label('cards'),
    ).filter(Card.yellow == yellow).group_by(Card.player).order_by(db.func.count(Card.player).desc()).all()

    top_scorers = []
    count = 1
    for top_player in statistics:

        player = Player.query.filter_by(player_id=top_player.player).first()

        top_scorers.append(
            dict(
                image=get_player_image(player.name, small=True),
                player=player.name,
                goals=top_player.cards,
                id=player.player_id
            )
        )

        if count == 10:
            break
        count += 1

    return top_scorers
