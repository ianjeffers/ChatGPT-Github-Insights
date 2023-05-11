import pinecone
import ast
from transformers import AutoTokenizer, AutoModel
from slimit.parser import Parser
from slimit.visitors import nodevisitor

tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
model = AutoModel.from_pretrained("microsoft/codebert-base")

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
pinecone.init(api_key=PINECONE_API_KEY, environment="us-west1-gcp-free")


def get_functions_from_py_code(code):
    tree = ast.parse(code)
    functions = []
    # Traverse the parsed code
    for node in ast.walk(tree):
        # Check if the node is a function
        if isinstance(node, ast.FunctionDef):
            function_code = ast.unparse(node)
            function_name = node.name
            functions.append((function_code, {"name": function_name}))

    return functions

def get_functions_from_js_code(js_code):
    parser = Parser()
    tree = parser.parse(js_code)
    functions = []
    for node in nodevisitor.visit(tree):
        if isinstance(node, ast.FunctionDeclaration):
            function_code = js_code[node.location.start_position.offset:node.location.end_position.offset]
            function_name = node.identifier.name
            functions.append((function_code, {"name": function_name}))

    return functions


def get_classes_from_py_code(code):
    tree = ast.parse(code)
    classes = []
    # Traverse the parsed code
    for node in ast.walk(tree):
        # Check if the node is a class
        if isinstance(node, ast.ClassDef):
            class_code = ast.unparse(node)
            class_name = node.name
            classes.append((class_code, {"name": class_name}))

    return classes

def get_classes_from_js_code(js_code):
    parser = Parser()
    tree = parser.parse(js_code)
    classes = []
    for node in nodevisitor.visit(tree):
        if isinstance(node, ast.ClassDeclaration):
            class_code = js_code[node.location.start_position.offset:node.location.end_position.offset]
            class_name = node.identifier.name
            methods = []
            for method in node.body:
                if isinstance(method, ast.MethodDefinition):
                    method_name = method.property.name if method.property else ''
                    methods.append(method_name)
            classes.append((class_code, {"name": class_name, "methods": methods}))
    return classes

def get_code_embedding(code):
    inputs = tokenizer(code, return_tensors='pt', padding=True, truncation=True, max_length=512)
    outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.detach().numpy()

def store_code_embeddings_in_pinecone(code_id, code_embedding):
    pinecone_client.upsert(items={code_id: code_embedding})

def query_code_embeddings_in_pinecone(query_embedding, top_k):
    # Query Pinecone for the top_k most similar vectors to query_embedding
    query_results = pinecone_client.query(queries=[query_embedding], top_k=top_k)
    # The results include the ids of the vectors and their similarity scores
    # For this method, we'll just return the ids (i.e., the code_ids)
    return query_results.ids[0]