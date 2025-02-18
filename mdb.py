import os
import re
from pprint import pprint
import sys
#xwris to import collections vgazei error  oti dn uparxei to attribute callable
#kalou kakou tha efarmostei se ola ta .py arxeia poy yparxei to readline
import collections
collections.Callable = collections.abc.Callable
import readline
import traceback
import shutil
sys.path.append('miniDB')

from database import Database
from table import Table
# art font is "big"
art = '''
             _         _  _____   ____  
            (_)       (_)|  __ \ |  _ \     
  _ __ ___   _  _ __   _ | |  | || |_) |
 | '_ ` _ \ | || '_ \ | || |  | ||  _ < 
 | | | | | || || | | || || |__| || |_) |
 |_| |_| |_||_||_| |_||_||_____/ |____/   2021 - v3.2                               
'''   


def search_between(s, first, last):
    '''
    Search in 's' for the substring that is between 'first' and 'last'
    '''
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
    except:
        return
    return s[start:end].strip()

def in_paren(qsplit, ind):
    '''
    Split string on space and return whether the item in index 'ind' is inside a parentheses
    '''
    return qsplit[:ind].count('(')>qsplit[:ind].count(')')


def create_query_plan(query, keywords, action):
    '''
    Given a query, the set of keywords that we expect to pe present and the overall action, return the query plan for this query.
    This can and will be used recursively
    '''

    dic = {val: None for val in keywords if val!=';'}

    ql = [val for val in query.split(' ') if val !='']

    kw_in_query = []
    kw_positions = []
    for i in range(len(ql)):
        if ql[i] in keywords and not in_paren(ql, i):
            kw_in_query.append(ql[i])
            kw_positions.append(i)
        elif i!=len(ql)-1 and f'{ql[i]} {ql[i+1]}' in keywords and not in_paren(ql, i):
            kw_in_query.append(f'{ql[i]} {ql[i+1]}')
            kw_positions.append(i+1)


    for i in range(len(kw_in_query)-1):
        dic[kw_in_query[i]] = ' '.join(ql[kw_positions[i]+1:kw_positions[i+1]])

    if action=='select':
        dic = evaluate_from_clause(dic)
        
        if dic['order by'] is not None:
            dic['from'] = dic['from'].removesuffix(' order')
            if 'desc' in dic['order by']:
                dic['desc'] = True
            else:
                dic['desc'] = False
            dic['order by'] = dic['order by'].removesuffix(' asc').removesuffix(' desc')
            
        else:
            dic['desc'] = None

    if action=='create table':
        args = dic['create table'][dic['create table'].index('('):dic['create table'].index(')')+1]
        dic['create table'] = dic['create table'].removesuffix(args).strip()
        arg_nopk = args.replace('primary key', '')[1:-1]
        arglist = [val.strip().split(' ') for val in arg_nopk.split(',')]
        dic['column_names'] = ','.join([val[0] for val in arglist])
        dic['column_types'] = ','.join([val[1] for val in arglist])
        if 'primary key' in args:
            arglist = args[1:-1].split(' ')
            dic['primary key'] = arglist[arglist.index('primary')-2]
        else:
            dic['primary key'] = None
    #
    #efoson thelei temp view tha prepei to value na ein distinct wste na to vriskei, allios na emfanizei tis grammes me omoia data,alliws sunexise.
    #if action=='create view':
        #select sugkekrimena stoixeia
        #kai emfanise
    #if drop view
        #delete temp view
    if action=='create view':
        #if create view select from table those columns and show
        #isxws xreiastei kainourgia def gia na ektelei authn thn leitourgia 
        args = dic['create view'][dic['create view'].index('('):dic['create view'].index(')')+1]
        dic['create view'] = dic['create view'].removesuffix(args).strip()
        arg_nopk = args.replace('primary key', '')[1:-1]
        arglist = [val.strip().split(' ') for val in arg_nopk.split(',')]
        #perittes prakseis katwhs columns kai rows tha parouem apo new pinaka
        #dic['column_names'] = ','.join([val[0] for val in arglist])
        #dic['column_types'] = ','.join([val[1] for val in arglist])
        #Apla gia safeguard feature ,logika einai axreiasto alla kalutera na pernaei elegxo ki apla na to pernaei
        if 'primary key' in args:
            arglist = args[1:-1].split(' ')
            dic['primary key'] = arglist[arglist.index('primary')-2]
        else:
            dic['primary key'] = None
        ## efoson theloume apo allo pinaka  isws na na xreiastei h from edw 
        if dic['order by'] is not None:
            dic['from'] = dic['from'].removesuffix(' order')
    
        
    
   
    
    if action=='import': 
        dic = {'import table' if key=='import' else key: val for key, val in dic.items()}

    if action=='insert into':
        # eisagoume ston epilegmeno pinaka
        if dic['select'] is not None:  # an h select propuarxei
            dic = evaluate_from_clause(dic)  #apla emfanise
        #allios sunexise
        elif dic['values'][0] == '(' and dic['values'][-1] == ')':
            dic['values'] = dic['values'][1:-1]
        else:
            raise ValueError('Your parens are not right m8')
    
    if action=='unlock table':
        if dic['force'] is not None:
            dic['force'] = True
        else:
            dic['force'] = False

    return dic



def evaluate_from_clause(dic):
    '''
    Evaluate the part of the query (argument or subquery) that is supplied as the 'from' argument
    '''
    join_types = ['inner', 'left', 'right', 'full']
    from_split = dic['from'].split(' ')
    if from_split[0] == '(' and from_split[-1] == ')':
        subquery = ' '.join(from_split[1:-1])
        dic['from'] = interpret(subquery)

    join_idx = [i for i,word in enumerate(from_split) if word=='join' and not in_paren(from_split,i)]
    on_idx = [i for i,word in enumerate(from_split) if word=='on' and not in_paren(from_split,i)]
    if join_idx:
        join_idx = join_idx[0]
        on_idx = on_idx[0]
        join_dic = {}
        if from_split[join_idx-1] in join_types:
            join_dic['join'] = from_split[join_idx-1]
            join_dic['left'] = ' '.join(from_split[:join_idx-1])
        else:
            join_dic['join'] = 'inner'
            join_dic['left'] = ' '.join(from_split[:join_idx])
        join_dic['right'] = ' '.join(from_split[join_idx+1:on_idx])
        join_dic['on'] = ''.join(from_split[on_idx+1:])

        if join_dic['left'].startswith('(') and join_dic['left'].endswith(')'):
            join_dic['left'] = interpret(join_dic['left'][1:-1].strip())

        if join_dic['right'].startswith('(') and join_dic['right'].endswith(')'):
            join_dic['right'] = interpret(join_dic['right'][1:-1].strip())

        dic['from'] = join_dic
        
    return dic

def interpret(query):
    '''
    Interpret the query.
    Added create temp view and dropp temp view san kainourgia actions
    '''
    kw_per_action = {'create table': ['create table'],
                     'drop table': ['drop table'],
                     'cast': ['cast', 'from', 'to'],
                     'import': ['import', 'from'],
                     'export': ['export', 'to'],
                     'insert into': ['insert into', 'values','select','from','where'],
                     'select': ['select', 'from', 'where', 'order by', 'top'],
                     'lock table': ['lock table', 'mode'],
                     'unlock table': ['unlock table', 'force'],
                     'delete from': ['delete from', 'where'],
                     'update table': ['update table', 'set', 'where'],
                     'create index': ['create index', 'on', 'using'],
                     'drop index': ['drop index'],
                     'create view': ['create view'],
                     'drop view': ['drop view']

                     }

    if query[-1]!=';':
        query+=';'
    
    query = query.replace("(", " ( ").replace(")", " ) ").replace(";", " ;").strip()

    for kw in kw_per_action.keys():
        if query.startswith(kw):
            action = kw

    return create_query_plan(query, kw_per_action[action]+[';'], action)

def execute_dic(dic):
    '''
    Execute the given dictionary
    '''
    for key in dic.keys():
        if isinstance(dic[key],dict):
            dic[key] = execute_dic(dic[key])
    
    action = list(dic.keys())[0].replace(' ','_')
    return getattr(db, action)(*dic.values())

def interpret_meta(command):
    """
    Interpret meta commands. These commands are used to handle DB stuff, something that can not be easily handled with mSQL given the current architecture.
    The available meta commands are:
    lsdb - list databases
    lstb - list tables
    cdb - change/create database
    rmdb - delete database
    """
    action = command[1:].split(' ')[0].removesuffix(';')

    db_name = db._name if search_between(command, action,';')=='' else search_between(command, action,';')

    def list_databases(db_name):
        [print(fold.removesuffix('_db')) for fold in os.listdir('dbdata')]
    
    def list_tables(db_name):
        [print(pklf.removesuffix('.pkl')) for pklf in os.listdir(f'dbdata/{db_name}_db') if pklf.endswith('.pkl')\
            and not pklf.startswith('meta')]

    def change_db(db_name):
        global db
        db = Database(db_name, load=True)
    
    def remove_db(db_name):
        shutil.rmtree(f'dbdata/{db_name}_db')

    commands_dict = {
        'lsdb': list_databases,
        'lstb': list_tables,
        'cdb': change_db,
        'rmdb': remove_db,
    }

    commands_dict[action](db_name)


if __name__ == "__main__":
    fname = os.getenv('SQL')
    dbname = os.getenv('DB')

    db = Database(dbname, load=True)

    if fname is not None:
        for line in open(fname, 'r').read().splitlines():
            if line.startswith('--'): continue
            dic = interpret(line.lower())
            result = execute_dic(dic)
            if isinstance(result,Table):
                result.show()
    else:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

        print(art)
        session = PromptSession(history=FileHistory('.inp_history'))
        while 1:
            try:
                line = session.prompt(f'({db._name})> ', auto_suggest=AutoSuggestFromHistory()).lower()
                if line[-1]!=';':
                    line+=';'
            except (KeyboardInterrupt, EOFError):
                print('\nbye!')
                break
            try:
                if line=='exit':
                    break
                if line.startswith('.'):
                    interpret_meta(line)
                elif line.startswith('explain'):
                    dic = interpret(line.removeprefix('explain '))
                    pprint(dic, sort_dicts=False)
                else:
                    dic = interpret(line)
                    result = execute_dic(dic)
                    if isinstance(result,Table):
                        result.show()
            except Exception:
                print(traceback.format_exc())
