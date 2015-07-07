# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect
from django.utils import timezone
from django.contrib import auth
from django.core.context_processors import csrf
from Cerberus.forms import UserRegistrationForm
from django.template import RequestContext
from django.shortcuts import render, render_to_response
from .forms import UploadFileForm, TurmaCreationForm, AtividadeCreationForm
from Aeacus import compare
from Athena.models import Aluno
from Athena.models import Turma
from Athena.models import Atividade
from Athena.models import Submissao
from Athena.models import RelAlunoAtividade
from Athena.utils import checar_login_professor, checar_login_aluno
from pprint import pprint
import re


def login(request):

    professor = checar_login_professor(request)
    aluno = checar_login_aluno(request)

    if professor:
        return HttpResponseRedirect('/professor')
    if aluno:
        return HttpResponseRedirect('/aluno')

    if request.method == 'POST':

        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)

            matchObjAluno = re.match(
                r'(.*)@aluno.ita.br$', user.email, re.M | re.I)

            if matchObjAluno:
                return HttpResponseRedirect('/aluno')
            return HttpResponseRedirect('/professor')

        else:
            return render_to_response(
                'login.html',
                {"invalid_message": "Login inválido. Tente novamente."},
                context_instance=RequestContext(request),
            )

    return render_to_response('login.html',
                              {"invalid_message": ""},
                              context_instance=RequestContext(request))


def register_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return render_to_response(
                'cadastro.html',
                {"success_message": "O cadastro foi realizado com sucesso!"},
                context_instance=RequestContext(request),
            )

    else:
        form = UserRegistrationForm()
    args = {}
    args.update(csrf(request))

    args['form'] = form

    return render_to_response('cadastro.html', args)


def home(request):

    if request.user.is_authenticated():
        form = UploadFileForm()
        if request.method == 'POST':
            entrada = request.FILES.getlist('file')[0]
            saida = request.FILES.getlist('file')[1]
            fonte = request.FILES.getlist('file')[2]

            resultado = compare.mover(entrada, saida, fonte)

            return render(
                request, 'teste_juiz.html',
                {
                    'form': form,
                    'resultado': resultado,
                }
            )

        return render(request, 'teste_juiz.html', {'form': form})

    else:
        return HttpResponseRedirect('/login')


def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/login')


def professor(request):

    professor = checar_login_professor(request)

    if not professor:
        return HttpResponseRedirect('/login')

    professor = professor[0]

    form = TurmaCreationForm()
    if request.method == 'POST':
        pprint(request.POST)
        if('post_turma' in request.POST):
            turma = Turma(
                nome=request.POST['nome'],
                descricao=request.POST['descricao'],
                professor=professor,
            )
            turma.save()
        elif ('post_atividade' in request.POST):
            turma = Turma.objects.get(id=request.POST['id_turma'])
            turma_id = turma.id
            prefixo = str(turma_id) + '-'
            atividade = Atividade(
                nome=request.POST[prefixo + 'nome'],
                descricao=request.POST[prefixo + 'descricao'],
                data_limite=request.POST[prefixo + 'data_limite'],
                arquivo_roteiro=request.FILES[prefixo + 'arquivo_roteiro'],
                arquivo_entrada=request.FILES[prefixo + 'arquivo_entrada'],
                arquivo_saida=request.FILES[prefixo + 'arquivo_saida'],
                turma=turma,
            )
            atividade.save()
        elif ('post_deletar' in request.POST):
            turma = Turma.objects.get(id=request.POST['id_turma'])
            turma.delete()

    turmas = Turma.objects.filter(professor=professor)
    panes = []
    for turma in turmas:
        atividades = Atividade.objects.filter(turma=turma)
        panes.append(
            render_to_response(
                'pane_professor.html',
                {
                    "turma": turma,
                    "atividades": atividades,
                    "form": AtividadeCreationForm(prefix=turma.id),
                },
                context_instance=RequestContext(request),
            ).content
        )

    return render_to_response(
        'professor.html',
        {"turmas": turmas,
         "panes": panes,
         "form": form},
        context_instance=RequestContext(request),
    )


def prof_ativ(request, id_ativ):

    professor = checar_login_professor(request)

    if not professor:
        return HttpResponseRedirect('/login')

    atividade = Atividade.objects.get(id=id_ativ)
    # atividade1 = Atividade.objects.get(id=request.GET.get('id_ativ'))

    status_aluno = []

    for aluno in atividade.turma.alunos.all():
        submissao = Submissao.objects.filter(atividade=atividade, aluno=aluno)
        if submissao:
            submissao = submissao[0]

            status_aluno.append(
                (aluno.nome, submissao.data_envio, submissao.resultado)
            )
        else:
            status_aluno.append(
                (aluno.nome, "Não enviado", "-")
            )

    return render_to_response(
        'prof_ativ.html',
        {
            "atividade": atividade,
            "status_aluno": status_aluno,
        },
        context_instance=RequestContext(request),
    )


def aluno(request):

    aluno = checar_login_aluno(request)

    if not aluno:
        return HttpResponseRedirect('/login')

    aluno = aluno[0]

    turmas = aluno.turma_set.all()
    panes = []
    for turma in turmas:

        tuple_ativ_subm = []
        atividades = Atividade.objects.filter(turma=turma)

        for atividade in atividades:
            submissao = Submissao.objects.filter(
                atividade=atividade,
                aluno=aluno,
            )
            if submissao:
                submissao = submissao[len(submissao)-1]

            tuple_ativ_subm.append([atividade, submissao])

        panes.append(
            render_to_response(
                'pane_aluno.html',
                {
                    "aluno": aluno,
                    "turma": turma,
                    "tuple_ativ_subm": tuple_ativ_subm,
                },
                context_instance=RequestContext(request),
            ).content
        )

    return render_to_response(
        'aluno.html',
        {"turmas": turmas,
         "panes": panes},
        context_instance=RequestContext(request),
    )


def aluno_ativ(request, ativ_id):
    aluno = Aluno.objects.filter(user=request.user)
    if request.user.is_authenticated() is False or not aluno:
        return HttpResponseRedirect('/login')
    aluno = aluno[0]

    atividade = Atividade.objects.filter(id=ativ_id)
    if not atividade:
        return HttpResponseRedirect('/aluno')
    atividade = atividade[0]
    resultado = ""

    relAlunoAtividade = RelAlunoAtividade.objects.filter(
        aluno=aluno,
        atividade=atividade
    )
    if relAlunoAtividade:
        relAlunoAtividade = relAlunoAtividade[0]

    if request.method == 'POST':

        atividade.arquivo_entrada.open()
        entrada = atividade.arquivo_entrada.read()
        atividade.arquivo_entrada.close()

        atividade.arquivo_saida.open()
        saida = atividade.arquivo_saida.read()
        atividade.arquivo_saida.close()

        fonte = request.FILES['arquivo_codigo']

        status, resultado = compare.mover(entrada, saida, fonte)
        pprint(status)
        nota = 0
        if status == "WA":
            nums = []
            for s in resultado.split():
                if s.isdigit():
                    nums.append(int(s))
            num_diffs = nums[0]
            lines_diff = resultado.count('<br>') - 2
            pprint(lines_diff)
            nota = (((lines_diff - num_diffs)*100.0)/lines_diff)
            nota = int(nota)
        if status == "AC":
            nota = 100

        submissao = Submissao(
            data_envio=timezone.now().date(),
            arquivo_codigo=request.FILES['arquivo_codigo'],
            resultado=status,
            nota=nota,
            atividade=atividade,
            aluno=aluno,
        )
        submissao.save()

        if relAlunoAtividade:
            relAlunoAtividade.foiEntregue = True
        else:
            relAlunoAtividade = RelAlunoAtividade(
                foiEntregue=True,
                aluno=aluno,
                atividade=atividade,
            )
        relAlunoAtividade.save()

    submissao = Submissao.objects.filter(
        atividade=atividade,
        aluno=aluno
    )
    status = "Nao entregue"
    if submissao:
        submissao = submissao[len(submissao) - 1]
        status = submissao.resultado

    return render_to_response(
        'aluno_ativ.html',
        {
            "atividade": atividade,
            "submissao": submissao,
            "relAlunoAtividade": relAlunoAtividade,
            "resultado": resultado,
            "status": status,
        },
        context_instance=RequestContext(request),
    )


def aluno_turmas(request):
    aluno = Aluno.objects.filter(user=request.user)
    if request.user.is_authenticated() is False or not aluno:
        return HttpResponseRedirect('/login')
    aluno = aluno[0]

    if request.method == 'POST':
        pprint(request.POST)
        if('post_sair' in request.POST):
            turma = Turma.objects.get(id=request.POST['post_sair'])
            aluno.turma_set.remove(turma)
            aluno.save()
        if('post_entrar' in request.POST):
            turma = Turma.objects.get(id=request.POST['post_entrar'])
            aluno.turma_set.add(turma)
            aluno.save()

    turmas_registradas = aluno.turma_set.all()
    todas_turmas = Turma.objects.all()
    turmas_nao_registradas = todas_turmas.exclude(
        id__in=[turma_check.id for turma_check in turmas_registradas]
    )

    return render_to_response(
        'lista_turmas.html',
        {
            "turmas_registradas": turmas_registradas,
            "turmas_nao_registradas": turmas_nao_registradas,
        },
        context_instance=RequestContext(request),
    )
