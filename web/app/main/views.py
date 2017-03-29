from urllib.parse import urlparse

from flask import render_template, jsonify, flash, redirect, url_for
from flask_login import current_user

from links.usecases.bookmarks import BookmarkDetailsUseCase, CreateBookmarkUseCase, \
    ListBookmarksUseCase
from links.usecases.interfaces import OutputBoundary, View, Controller
from web.app.main.formatting import format_display_date, format_iso_date
from . import forms
from . import main


@main.route('/bookmarks')
def index():
    print(current_user.get_id())
    controller = BookmarkListController(
        ListBookmarksUseCase(),
        BookmarkListPresenter(),
        BookmarkListView())
    return controller.handle({'user_id': current_user.get_id()})


@main.route('/bookmarks/<string:bookmark_id>')
def bookmark_details(bookmark_id):
    uc = BookmarkDetailsUseCase()
    presenter = BookmarkDetailsPresenter()
    view = BookmarkDetailsView()
    controller = BookmarkDetailsController(uc, presenter, view)
    return controller.handle({'user_id': current_user.get_id(), 'bookmark_id': bookmark_id})


@main.route('/bookmarks.json')
def json_index():
    uc = ListBookmarksUseCase()
    presenter = BookmarkListPresenter()
    view = BookmarkListJSONView()
    controller = BookmarkListController(uc, presenter, view)
    try:
        return controller.handle({'user_id': current_user.get_id()})
    except Exception:
        return jsonify({'error': 'Something bad happened'})


@main.route('/create', methods=['GET', 'POST'])
def create():
    form = forms.CreateBookmarkForm()

    if form.validate_on_submit():
        uc = CreateBookmarkUseCase()
        presenter = CreateBookmarkPresenter()
        view = CreateBookmarkView(form)
        controller = CreateBookmarkController(uc, presenter, view)
        # View will redirect or regenerate form.
        request = {'user_id': current_user.get_id(), 'form': form}
        return controller.handle(request)

    return render_template('create_bookmark.html', form=form)


#
# Interface Implementations
#

def format_bookmark_details(bookmark):
    """

    :param bookmark: bookmark details namedtuple
    :return: dict
    """
    return {
        'bookmark_id': bookmark.bookmark_id,
        'name': bookmark.name,
        'url': bookmark.url,
        'date_created': format_display_date(bookmark.date_created),
        'date_created_iso': format_iso_date(bookmark.date_created),
        'host': urlparse(bookmark.url).netloc,
    }


class BaseController(Controller):
    """A generic controller implementation that suites most use cases"""

    def __init__(self, usecase, presenter, view):
        self.usecase = usecase
        self.presenter = presenter
        self.view = view


class BookmarkListController(BaseController):

    def handle(self, request):
        self.usecase.list_bookmarks(request['user_id'], self.presenter)
        return self.view.generate_view(self.presenter.get_view_model())


class BookmarkListPresenter(OutputBoundary):
    """A basic, default implementation of a presenter for this use case"""

    def __init__(self):
        self._view_model = []

    def get_view_model(self):
        return self._view_model

    def present(self, bookmarks):
        """

        :param bookmarks: list of bookmark details namedtuple
        :return:
        """
        self._view_model = [format_bookmark_details(bm) for bm in bookmarks]


class BookmarkListView(View):

    def generate_view(self, view_model):
        return render_template('list_bookmarks.html', bookmarks=view_model)


class BookmarkListJSONView(View):

    def generate_view(self, view_model):
        return jsonify(
            {'bookmarks': [bookmark for bookmark in view_model]})


class CreateBookmarkController(BaseController):

    def handle(self, request):
        user_id = request['user_id']
        form = request['form']
        self.view.form = form
        self.usecase.create_bookmark(user_id, form.name.data, form.url.data, self.presenter)
        return self.view.generate_view(self.presenter.get_view_model())


class CreateBookmarkPresenter(OutputBoundary):

    def __init__(self):
        self._view_model = {}

    def present(self, response_model):
        self._view_model['bookmark_id'] = response_model.bookmark_id
        self._view_model['errors'] = {
            key: val for key, val in response_model.errors.items()
        }

    def get_view_model(self):
        return self._view_model


class CreateBookmarkView(View):

    form = None

    def __init__(self, form):
        self.form = form

    def generate_view(self, view_model):
        if view_model['errors']:
            self._set_form_errors(view_model)
            return render_template('create_bookmark.html', form=self.form)

        # on success flash a message and redirect
        flash('Data saved!', 'info')
        return redirect(url_for('main.index'))

    def _set_form_errors(self, view_model):
        """
        Set form errors returned by the use case. This is not flask-wtf's auto form
        error filler thing.
        :param view_model:
        :return:
        """
        errors = view_model['errors']
        for key, error in errors.items():
            try:
                field = getattr(self.form, key)
            except AttributeError:
                continue
            field.errors.extend(view_model['errors'][key])


class BookmarkDetailsController(BaseController):

    def handle(self, request):
        self.usecase.bookmark_details(request['user_id'], request['bookmark_id'], self.presenter)
        return self.view.generate_view(self.presenter.get_view_model())


class BookmarkDetailsPresenter(OutputBoundary):

    def __init__(self):
        self._view_model = {}

    def get_view_model(self):
        return self._view_model

    def present(self, bookmark_details):
        self._view_model = format_bookmark_details(bookmark_details)


class BookmarkDetailsView(View):

    def generate_view(self, view_model):
        return render_template('bookmark_details.html', bookmark=view_model)
