from setuptools import setup
setup(name='surecheck-mcp', version='0.1.1', py_modules=['surecheck_mcp'],
      description='Local stdio MCP wrapper for GTM Agent One phone metadata and email syntax/DNS',
      python_requires='>=3.8', entry_points={'console_scripts':['surecheck-mcp=surecheck_mcp:main']})
