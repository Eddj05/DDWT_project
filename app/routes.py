from flask import render_template, flash, request, redirect, url_for, abort, jsonify
from app import db
from flask import current_app as app
from app.forms import LoginForm, EmptyForm, PostForm, EditProfileForm, RegistrationForm
from flask_login import current_user, login_user, login_required, logout_user
import sqlalchemy as sa
from app.models import User, Post
from urllib.parse import urlsplit
from datetime import datetime, timezone


def init_routes(app):
    @app.route('/', methods=['GET', 'POST'])
    @app.route('/index', methods=['GET', 'POST'])
    @login_required
    def index():
        form = PostForm()
        if form.validate_on_submit():
            post = Post(
                title=form.title.data,
                description=form.description.data,
                price=form.price.data,
                servings=form.servings.data,
                prep_time=form.prep_time.data,
                recipe_text=form.recipe_text.data,
                author=current_user
            )
            db.session.add(post)
            db.session.commit()
            flash('Your post is now live!')
            return redirect(url_for('index'))
        page = request.args.get('page', 1, type=int)
        posts = db.paginate(current_user.following_posts(), page=page,
                            per_page=app.config['POSTS_PER_PAGE'], error_out=False)
        next_url = url_for('index', page=posts.next_num) \
            if posts.has_next else None
        prev_url = url_for('index', page=posts.prev_num) \
            if posts.has_prev else None
        return render_template('index.html', title='Home', form=form,
                            posts=posts.items, next_url=next_url,
                            prev_url=prev_url)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = LoginForm()
        if form.validate_on_submit():
            user = db.session.scalar(
                sa.select(User).where(User.username == form.username.data))
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password')
                return redirect(url_for('login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or urlsplit(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        return render_template('login.html', title='Sign In', form=form)

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Congratulations, you are now a registered user!')
            return redirect(url_for('login'))
        return render_template('register.html', title='Register', form=form)

    @app.route('/user/<username>')
    @login_required
    def user(username):
        user = db.first_or_404(sa.select(User).where(User.username == username))
        page = request.args.get('page', 1, type=int)
        query = user.posts.select().order_by(Post.timestamp.desc())
        posts = db.paginate(query, page=page,
                            per_page=app.config['POSTS_PER_PAGE'],
                            error_out=False)
        next_url = url_for('user', username=user.username, page=posts.next_num) \
            if posts.has_next else None
        prev_url = url_for('user', username=user.username, page=posts.prev_num) \
            if posts.has_prev else None
        form = EmptyForm()
        return render_template('user.html', user=user, posts=posts.items,
                            next_url=next_url, prev_url=prev_url, form=form)


    @app.before_request
    def before_request():
        if current_user.is_authenticated:
            current_user.last_seen = datetime.now(timezone.utc)
            db.session.commit()

    @app.route('/edit_profile', methods=['GET', 'POST'])
    @login_required
    def edit_profile():
        form = EditProfileForm()
        if form.validate_on_submit():
            current_user.username = form.username.data
            current_user.about_me = form.about_me.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Your changes have been saved.')
            return redirect(url_for('user', username=current_user.username))
        elif request.method == 'GET':
            form.username.data = current_user.username
            form.about_me.data = current_user.about_me
            form.email.data = current_user.email
        return render_template('edit_profile.html', title='Edit Profile',
                            form=form)


    @app.route('/follow/<username>', methods=['POST'])
    @login_required
    def follow(username):
        form = EmptyForm()
        if form.validate_on_submit():
            user = db.session.scalar(
                sa.select(User).where(User.username == username))
            if user is None:
                flash(f'User {username} not found.')
                return redirect(url_for('index'))
            if user == current_user:
                flash('You cannot follow yourself!')
                return redirect(url_for('user', username=username))
            current_user.follow(user)
            db.session.commit()
            flash(f'You are following {username}!')
            return redirect(url_for('user', username=username))
        else:
            return redirect(url_for('index'))


    @app.route('/unfollow/<username>', methods=['POST'])
    @login_required
    def unfollow(username):
        form = EmptyForm()
        if form.validate_on_submit():
            user = db.session.scalar(
                sa.select(User).where(User.username == username))
            if user is None:
                flash(f'User {username} not found.')
                return redirect(url_for('index'))
            if user == current_user:
                flash('You cannot unfollow yourself!')
                return redirect(url_for('user', username=username))
            current_user.unfollow(user)
            db.session.commit()
            flash(f'You are not following {username}.')
            return redirect(url_for('user', username=username))
        else:
            return redirect(url_for('index'))

    @app.route('/explore')
    @login_required
    def explore():
        page = request.args.get('page', 1, type=int)
        query = (
        sa.select(Post)
        .join(Post.author)
        .where(Post.user_id != current_user.id)  # Exclude the current user's posts
        .order_by(Post.timestamp.desc())
    )
        posts = db.paginate(query, page=page,
                            per_page=app.config['POSTS_PER_PAGE'], error_out=False)
        next_url = url_for('explore', page=posts.next_num) \
            if posts.has_next else None
        prev_url = url_for('explore', page=posts.prev_num) \
            if posts.has_prev else None
        return render_template("explore.html", title='Explore', posts=posts.items,
                            next_url=next_url, prev_url=prev_url)


    @app.route('/add_recipe', methods=['GET', 'POST'])
    @login_required
    def add_recipe():
        form = PostForm()
        if form.validate_on_submit():
            post = Post(
                title=form.title.data,
                description=form.description.data,
                price=form.price.data,
                servings=form.servings.data,
                prep_time=form.prep_time.data,
                recipe_text=form.recipe_text.data,
                user_id=current_user.id
            )
            db.session.add(post)
            db.session.commit()
            flash('Your recipe has been added!', 'success')
            return redirect(url_for('explore'))
        return render_template('add_recipe.html', title='Add Recipe', form=form)

    @app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
    @login_required
    def edit_post(post_id):
        post = Post.query.get_or_404(post_id)

        # check if the logged-in user is the author of the post
        if post.author != current_user:
            flash('You can only edit your own posts!', 'danger')
            return redirect(url_for('explore'))

        form = PostForm(obj=post)

        if form.validate_on_submit():
            post.title = form.title.data
            post.description = form.description.data
            post.price = form.price.data
            post.servings = form.servings.data
            post.prep_time = form.prep_time.data
            post.recipe_text = form.recipe_text.data
            db.session.commit()
            flash('Your post has been updated!', 'success')
            return redirect(url_for('explore'))

        return render_template('edit_post.html', title='Edit Post', form=form, post=post)
    
    @app.route('/recipe/<int:post_id>')
    def recipe(post_id):
        # fetch the post by its ID
        post = Post.query.get(post_id)
        
        # return an error when the page isn't found
        if post is None:
            abort(404)

        title = post.title

        return render_template('recipe.html', post=post, title=title)

    @app.route('/delete_post/<int:post_id>', methods=['POST'])
    @login_required
    def delete_post(post_id):
        # fetch the post by its ID
        post = Post.query.get(post_id)
        
        # check if the post exists
        if not post:
            flash('Post not found!', 'danger')
            return redirect(url_for('explore'))
        
        try:
            # Check whether the current user is the author.
            if post.author != current_user:
                flash('You can only delete your own posts!', 'danger')
                return redirect(url_for('explore'))
            
            # delete post
            db.session.delete(post)
            db.session.commit()
            flash('Post deleted successfully!', 'success')
        
        except Exception as e:
            # error message
            flash('There was a problem deleting that post: ' + str(e), 'danger')
        
        return redirect(url_for('explore'))
    

    @app.route('/like/<int:post_id>', methods=['POST'])
    @login_required
    def like_recipe(post_id):
        # find the post by its ID
        post = Post.query.get_or_404(post_id)

        # check if the user has already liked the post
        if not current_user.has_liked_post(post):
            current_user.like_post(post)
        else:
            current_user.unlike_post(post)

        db.session.commit()

        # return the updated like count and liked status as JSON
        return jsonify({
            'likes_count': post.likes_count(),
            'liked': current_user.has_liked_post(post)
        })
    
    @app.route('/find_user', methods=['GET'])
    @login_required
    def find_user():
        username_query = request.args.get('username', '').strip()

        if username_query:
            # find users whose username starts with the query (sorted at the top)
            users_start = User.query.filter(User.username.ilike(f'{username_query}%')).all()

            # find users whose username contains the query (but doesn't start with it)
            users_contains = User.query.filter(User.username.ilike(f'%{username_query}%')).all()

            # combine the two lists: first the users who start with the query, then the others
            # and remove duplicates
            users = list({user.id: user for user in users_start + users_contains}.values())
        else:
            # if there's no search query, show all users
            users = User.query.all()

        return render_template('find_user.html', users=users, username_query=username_query)
    
    @app.route('/user/<int:user_id>')
    def view_user(user_id):
        user = User.query.get_or_404(user_id)
        form = EmptyForm()
        return render_template('user.html', user=user, form=form)