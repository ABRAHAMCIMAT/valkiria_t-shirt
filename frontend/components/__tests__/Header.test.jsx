import { render, screen } from '@testing-library/react';
import Header from '../Header';

describe('Header', () => {
  it('renderiza el título principal del sistema', () => {
    render(<Header />);

    expect(
      screen.getByText(/Modelo de Predicción PM/i)
    ).toBeInTheDocument();
  });

  it('renderiza el subtítulo descriptivo', () => {
    render(<Header />);

    expect(
      screen.getByText(/ML Ensemble.*RAG Excel.*Meta Llama.*Ollama/i)
    ).toBeInTheDocument();
  });
});
