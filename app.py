from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///discgolf.db'
app.config['SECRET_KEY'] = 'discgolf-local-secret'
db = SQLAlchemy(app)

CATEGORIES = ['MPO', 'FPO', 'MA3', 'FA3', 'MJ18']

# ── Models ────────────────────────────────────────────────────────────────────

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    holes = db.relationship('Hole', backref='course', cascade='all, delete-orphan', order_by='Hole.number')

class Hole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    default_par = db.Column(db.Integer, default=3)
    category_pars = db.relationship('HoleCategoryPar', backref='hole', cascade='all, delete-orphan')

    def par_for(self, category):
        cp = HoleCategoryPar.query.filter_by(hole_id=self.id, category=category).first()
        return cp.par if cp else self.default_par

class HoleCategoryPar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hole_id = db.Column(db.Integer, db.ForeignKey('hole.id'), nullable=False)
    category = db.Column(db.String(10), nullable=False)
    par = db.Column(db.Integer, nullable=False)

class Player(db.Model):
    """Global player registry — exists independently of any event."""
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(10), nullable=False)
    handicap = db.Column(db.Float, default=0)
    event_entries = db.relationship('EventPlayer', backref='global_player', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    num_rounds = db.Column(db.Integer, default=1)
    categories = db.Column(db.String(100))
    use_handicap = db.Column(db.Boolean, default=False)
    course = db.relationship('Course')
    players = db.relationship('EventPlayer', backref='event', cascade='all, delete-orphan')

    def categories_list(self):
        return [c.strip() for c in self.categories.split(',') if c.strip()] if self.categories else []

class EventPlayer(db.Model):
    """A player's entry in a specific event, with tournament-specific overrides."""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    category = db.Column(db.String(10), nullable=False)
    handicap = db.Column(db.Float, default=0)
    rounds = db.relationship('Round', backref='event_player', cascade='all, delete-orphan')

    @property
    def full_name(self):
        return self.global_player.full_name

    @property
    def first_name(self):
        return self.global_player.first_name

    @property
    def last_name(self):
        return self.global_player.last_name

class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('event_player.id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    scores = db.relationship('HoleScore', backref='round', cascade='all, delete-orphan', order_by='HoleScore.hole_number')

    def total_throws(self):
        return sum(s.throws for s in self.scores)

    def total_par(self):
        event = Event.query.get(self.event_id)
        ep = EventPlayer.query.get(self.player_id)
        return sum(h.par_for(ep.category) for h in event.course.holes)

    def to_par(self):
        return self.total_throws() - self.total_par()

    def to_par_handicap(self):
        ep = EventPlayer.query.get(self.player_id)
        return self.total_throws() - (self.total_par() + ep.handicap)

class HoleScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey('round.id'), nullable=False)
    hole_number = db.Column(db.Integer, nullable=False)
    throws = db.Column(db.Integer, nullable=False)

# ── Routes: Dashboard ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    courses = Course.query.all()
    events = Event.query.order_by(Event.date.desc()).all()
    player_count = Player.query.count()
    return render_template('index.html', courses=courses, events=events, player_count=player_count)

# ── Routes: Players ───────────────────────────────────────────────────────────

@app.route('/players')
def players():
    all_players = Player.query.order_by(Player.last_name, Player.first_name).all()
    return render_template('players.html', players=all_players, categories=CATEGORIES)

@app.route('/player/new', methods=['GET', 'POST'])
def new_player():
    if request.method == 'POST':
        player = Player(
            first_name=request.form['first_name'].strip(),
            last_name=request.form['last_name'].strip(),
            category=request.form['category'],
            handicap=float(request.form.get('handicap', 0))
        )
        db.session.add(player)
        db.session.commit()
        flash(f'{player.full_name} added to the registry!', 'success')
        return redirect(url_for('players'))
    return render_template('player_form.html', player=None, categories=CATEGORIES)

@app.route('/player/<int:player_id>/edit', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    if request.method == 'POST':
        player.first_name = request.form['first_name'].strip()
        player.last_name = request.form['last_name'].strip()
        player.category = request.form['category']
        player.handicap = float(request.form.get('handicap', 0))
        db.session.commit()
        flash(f'{player.full_name} updated!', 'success')
        return redirect(url_for('players'))
    return render_template('player_form.html', player=player, categories=CATEGORIES)

@app.route('/player/<int:player_id>/delete', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    name = player.full_name
    db.session.delete(player)
    db.session.commit()
    flash(f'{name} removed from registry.', 'info')
    return redirect(url_for('players'))

# ── Routes: Courses ───────────────────────────────────────────────────────────

@app.route('/course/new', methods=['GET', 'POST'])
def new_course():
    if request.method == 'POST':
        course = Course(name=request.form['name'], description=request.form.get('description', ''))
        db.session.add(course)
        db.session.flush()
        num_holes = int(request.form['num_holes'])
        for i in range(1, num_holes + 1):
            par = int(request.form.get(f'par_{i}', 3))
            db.session.add(Hole(course_id=course.id, number=i, default_par=par))
        db.session.commit()
        flash('Course created!', 'success')
        return redirect(url_for('course_detail', course_id=course.id))
    return render_template('course_form.html')

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course_detail.html', course=course, categories=CATEGORIES)

@app.route('/course/<int:course_id>/edit', methods=['GET', 'POST'])
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if request.method == 'POST':
        course.name = request.form['name']
        course.description = request.form.get('description', '')
        for hole in course.holes:
            hole.default_par = int(request.form.get(f'par_{hole.number}', hole.default_par))
            for cat in CATEGORIES:
                val = request.form.get(f'catpar_{hole.number}_{cat}', '').strip()
                existing = HoleCategoryPar.query.filter_by(hole_id=hole.id, category=cat).first()
                if val:
                    if existing:
                        existing.par = int(val)
                    else:
                        db.session.add(HoleCategoryPar(hole_id=hole.id, category=cat, par=int(val)))
                elif existing:
                    db.session.delete(existing)
        db.session.commit()
        flash('Course updated!', 'success')
        return redirect(url_for('course_detail', course_id=course.id))
    return render_template('course_edit.html', course=course, categories=CATEGORIES)

# ── Routes: Events ────────────────────────────────────────────────────────────

@app.route('/event/new', methods=['GET', 'POST'])
def new_event():
    courses = Course.query.all()
    if request.method == 'POST':
        cats = request.form.getlist('categories')
        event = Event(
            name=request.form['name'],
            course_id=int(request.form['course_id']),
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            description=request.form.get('description', ''),
            num_rounds=int(request.form['num_rounds']),
            categories=','.join(cats),
            use_handicap='use_handicap' in request.form
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created!', 'success')
        return redirect(url_for('event_detail', event_id=event.id))
    return render_template('event_form.html', courses=courses, categories=CATEGORIES)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    registered_ids = {ep.player_id for ep in event.players}
    available_players = Player.query.order_by(Player.last_name, Player.first_name).all()
    return render_template('event_detail.html', event=event, categories=CATEGORIES,
                           available_players=available_players, registered_ids=registered_ids)

@app.route('/event/<int:event_id>/add_player', methods=['POST'])
def add_player(event_id):
    event = Event.query.get_or_404(event_id)
    player_id = int(request.form['player_id'])
    player = Player.query.get_or_404(player_id)
    if EventPlayer.query.filter_by(event_id=event_id, player_id=player_id).first():
        flash(f'{player.full_name} is already registered.', 'info')
        return redirect(url_for('event_detail', event_id=event_id))
    ep = EventPlayer(
        event_id=event_id,
        player_id=player_id,
        category=request.form.get('category', player.category),
        handicap=float(request.form.get('handicap', player.handicap))
    )
    db.session.add(ep)
    db.session.commit()
    flash(f'{player.full_name} added to the event!', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/event/<int:event_id>/edit_player/<int:ep_id>', methods=['POST'])
def edit_event_player(event_id, ep_id):
    ep = EventPlayer.query.get_or_404(ep_id)
    ep.category = request.form['category']
    ep.handicap = float(request.form.get('handicap', ep.handicap))
    db.session.commit()
    flash(f'{ep.full_name} updated for this event.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/event/<int:event_id>/remove_player/<int:ep_id>', methods=['POST'])
def remove_player(event_id, ep_id):
    ep = EventPlayer.query.get_or_404(ep_id)
    name = ep.full_name
    db.session.delete(ep)
    db.session.commit()
    flash(f'{name} removed from event.', 'info')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/event/<int:event_id>/scores', methods=['GET', 'POST'])
def log_scores(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        player_id = int(request.form['player_id'])
        round_number = int(request.form['round_number'])
        existing = Round.query.filter_by(event_id=event_id, player_id=player_id, round_number=round_number).first()
        if existing:
            db.session.delete(existing)
            db.session.flush()
        rnd = Round(event_id=event_id, player_id=player_id, round_number=round_number)
        db.session.add(rnd)
        db.session.flush()
        for hole in event.course.holes:
            throws = int(request.form.get(f'hole_{hole.number}', 3))
            db.session.add(HoleScore(round_id=rnd.id, hole_number=hole.number, throws=throws))
        db.session.commit()
        flash('Scores saved!', 'success')
        return redirect(url_for('event_leaderboard', event_id=event_id))
    player_id = request.args.get('player_id', type=int)
    round_number = request.args.get('round', type=int, default=1)
    selected_player = EventPlayer.query.get(player_id) if player_id else None
    existing_round = None
    if selected_player:
        existing_round = Round.query.filter_by(event_id=event_id, player_id=player_id, round_number=round_number).first()
    return render_template('log_scores.html', event=event, selected_player=selected_player,
                           round_number=round_number, existing_round=existing_round)

@app.route('/event/<int:event_id>/leaderboard')
def event_leaderboard(event_id):
    event = Event.query.get_or_404(event_id)
    sort_by = request.args.get('sort', 'to_par')
    cat_filter = request.args.get('category', 'all')
    players = event.players
    if cat_filter != 'all':
        players = [p for p in players if p.category == cat_filter]
    results = []
    for ep in players:
        rounds = Round.query.filter_by(event_id=event_id, player_id=ep.id).order_by(Round.round_number).all()
        total_throws = sum(r.total_throws() for r in rounds)
        total_par = sum(r.total_par() for r in rounds)
        to_par = total_throws - total_par
        to_par_hcp = total_throws - (total_par + ep.handicap * len(rounds)) if rounds else 0
        results.append({
            'player': ep,
            'rounds': rounds,
            'total_throws': total_throws,
            'total_par': total_par,
            'to_par': to_par,
            'to_par_hcp': to_par_hcp,
            'rounds_played': len(rounds),
        })
    if sort_by == 'throws':
        results.sort(key=lambda x: x['total_throws'])
    elif sort_by == 'to_par_hcp':
        results.sort(key=lambda x: x['to_par_hcp'])
    else:
        results.sort(key=lambda x: x['to_par'])
    return render_template('leaderboard.html', event=event, results=results,
                           sort_by=sort_by, cat_filter=cat_filter, categories=CATEGORIES)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
