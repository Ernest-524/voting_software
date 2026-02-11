from django.urls import path
from . import views as main_views

urlpatterns = [
    path('login/', main_views.CustomLoginView.as_view(), name='login'),
    path('user_home/', main_views.user_homepage, name='user_homepage'),
    path('logout/', main_views.logout_view, name='logout'),
    path('admin_home/', main_views.admin_homepage, name='admin_homepage'),
    path('manage_positions/', main_views.manage_positions, name='manage_positions'),
    path('register_position/', main_views.register_position, name='register_position'),
    path('manage_candidates/', main_views.manage_candidates, name='manage_candidates'),
    path('register_candidate/', main_views.register_candidate, name='register_candidate'),
    path('vote/', main_views.vote_view, name='vote'),
    path('manage_vote/', main_views.manage_vote_dashboard, name='manage_vote_dashboard'),
    path('voters/', main_views.voter_list, name='voter_list'),
    path('voted/', main_views.voted_list, name='voted_list'),
    path('vote_results/', main_views.vote_results, name='vote_results'),
    path('not-voted/', main_views.not_voted_list, name='not_voted_list'),
    path('candidate-voters/<int:candidate_id>/', main_views.candidate_voters, name='candidate_voters'),
    path('vote_results/pdf/', main_views.export_vote_results_pdf, name='vote_results_pdf'),
    path('manage_election/', main_views.manage_election, name='manage_election'),
    path('start_election/', main_views.start_election_manual, name='start_election'),
    path('stop_election/', main_views.stop_election_manual, name='stop_election'),
    path('send-credentials/', main_views.send_credentials_view, name='send_credentials'),
    path('test-email/', main_views.test_email_view, name='test_email'),
    path('csrf-test/', main_views.csrf_test, name='csrf_test'),
]