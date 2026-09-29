# 📚 Documentação Técnica - Lógica de Funcionamento

Esta aplicação não imprime ficheiros de forma convencional. Ela atua como um "middleware" de texto (ZPL) entre o SAP e a impressora Zebra.

### 1. Leitura e Extração (PDF.js)
Os ficheiros gerados pelo SAP são PDFs que não contêm imagens, mas sim texto bruto que representa o código ZPL. O sistema utiliza a biblioteca `pdf.js` para iterar por todas as páginas do documento e concatenar o texto num único bloco de String, recriando o código ZPL original.

### 2. Renderização Visual (Canvas)
Para desenhar a pré-visualização:
- O sistema divide o código ZPL procurando por comandos de posicionamento `^FO` (Field Origin) e dados `^FD` (Field Data).
- Extrai as coordenadas X e Y.
- Multiplica os valores pela constante de conversão (`PX_POR_MM`) para simular a resolução de ecrã (203 DPI da impressora adaptados para o navegador).
- Desenha blocos (para simular códigos de barras `^BC`) e texto nativo.

### 3. Injeção de Dados e Impressão
A principal restrição deste projeto é **não alterar as escalas originais da etiqueta**. 
Por isso, a injeção da Data de Validade é feita de forma não destrutiva:
1. O utilizador define a posição visual, que é convertida de volta para milímetros.
2. O sistema constrói um novo campo ZPL: `^FO{x},{y}^A0N,{h},{h}^FH\^FD{texto}^FS`.
3. Se o utilizador definir uma quantidade > 1, o comando `^PQ{quantidade}` é adicionado.
4. O sistema procura o comando de fecho `^XZ` (Fim da Etiqueta) e injeta os novos campos imediatamente antes dele.
5. O resultado é encapsulado num `Blob` e descarregado como formato `.zpl`, garantindo que os drivers da Zebra interpretem o ficheiro na sua linguagem nativa, evitando desconfigurações de escala.
