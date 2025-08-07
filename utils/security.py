"""
安全工具模块
提供代码执行安全检查、认证和授权功能
"""

import ast
import re
import hashlib
import hmac
import time
from typing import List, Set, Dict, Any, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from config.settings import config
from utils.logger import get_logger

logger = get_logger("security")

class CodeSecurityChecker:
    """代码安全检查器"""
    
    def __init__(self):
        self.forbidden_modules = {
            'os', 'sys', 'subprocess', 'shutil', 'tempfile',
            'socket', 'urllib', 'requests', 'http', 'ftplib',
            'smtplib', 'poplib', 'imaplib', 'telnetlib',
            'multiprocessing', 'threading', 'asyncio',
            'pickle', 'marshal', 'ctypes', 'mmap',
            'signal', 'pwd', 'grp', 'crypt', 'termios',
            'fcntl', 'select', 'epoll', 'kqueue',
            'builtins', '__builtins__', '__import__',
            'eval', 'exec', 'compile', 'input'
        }
        
        self.forbidden_functions = {
            'eval', 'exec', 'compile', 'input', 'raw_input',
            'open', 'file', 'reload', 'delattr', 'setattr',
            'getattr', 'hasattr', 'vars', 'locals', 'globals',
            'dir', 'type', 'isinstance', 'issubclass',
            'super', 'property', 'staticmethod', 'classmethod'
        }
    
    def check_code_safety(self, code: str) -> Dict[str, Any]:
        """检查代码安全性"""
        try:
            # 检查代码大小
            if len(code.encode('utf-8')) > config.MAX_CODE_SIZE:
                return {
                    "safe": False,
                    "error": "代码大小超过限制",
                    "details": f"代码大小: {len(code.encode('utf-8'))} bytes, 限制: {config.MAX_CODE_SIZE} bytes"
                }
            
            # 解析AST
            tree = ast.parse(code)
            
            # 检查导入语句
            import_issues = self._check_imports(tree)
            if import_issues:
                return {
                    "safe": False,
                    "error": "检测到禁止的导入",
                    "details": import_issues
                }
            
            # 检查函数调用
            function_issues = self._check_function_calls(tree)
            if function_issues:
                return {
                    "safe": False,
                    "error": "检测到禁止的函数调用",
                    "details": function_issues
                }
            
            return {"safe": True, "message": "代码安全检查通过"}
            
        except SyntaxError as e:
            return {
                "safe": False,
                "error": "代码语法错误",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"代码安全检查异常: {e}")
            return {
                "safe": False,
                "error": "代码安全检查失败",
                "details": str(e)
            }
    
    def _check_imports(self, tree: ast.AST) -> List[str]:
        """检查导入语句"""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.forbidden_modules:
                            issues.append(f"禁止导入模块: {alias.name}")
                else:  # ImportFrom
                    if node.module in self.forbidden_modules:
                        issues.append(f"禁止从模块导入: {node.module}")
        
        return issues
    
    def _check_function_calls(self, tree: ast.AST) -> List[str]:
        """检查函数调用"""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.forbidden_functions:
                        issues.append(f"禁止的函数调用: {node.func.id}")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.forbidden_functions:
                        issues.append(f"禁止的方法调用: {node.func.attr}")
        
        return issues

class AuthenticationManager:
    """认证管理器"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = config.JWT_SECRET_KEY
        self.algorithm = config.JWT_ALGORITHM
        self.expiration_delta = config.JWT_EXPIRATION_DELTA
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = time.time() + self.expiration_delta.total_seconds()
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.error(f"令牌验证失败: {e}")
            return None

# 创建全局实例
code_checker = CodeSecurityChecker()
auth_manager = AuthenticationManager() 