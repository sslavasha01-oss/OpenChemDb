import java.sql.*;
import java.util.Properties;

import com.actelion.research.chem.IDCodeParser;
import com.actelion.research.chem.StereoMolecule;
import com.actelion.research.chem.MolfileCreator;

public class App {

    private static final String DB_URL = "jdbc:postgresql://localhost:5433/archive_db";
    private static final String USER = "chemist";
    private static final String PASSWORD = "archive_pass";

    static {
        java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"));
        System.setProperty("user.timezone", "UTC");
    }

    public static void main(String[] args) {
        System.out.println("=== PRODUCTION MOLFILE PARSING ===");

        Properties props = new Properties();
        props.setProperty("user", USER);
        props.setProperty("password", PASSWORD);

        IDCodeParser parser = new IDCodeParser();

        try (Connection conn = DriverManager.getConnection(DB_URL, props)) {

            String selectQuery = "SELECT id, idcode, id_coords_2d FROM book_base WHERE id = 48673;";
            String cleanMolfile = "";

            // 1. Извлекаем данные из book_base и генерируем чистый Molfile
            try (PreparedStatement selectStmt = conn.prepareStatement(selectQuery);
                 ResultSet rs = selectStmt.executeQuery()) {
                if (rs.next()) {
                    StereoMolecule mol = new StereoMolecule();
                    parser.parse(mol, rs.getString("idcode"), rs.getString("id_coords_2d"));

                    MolfileCreator creator = new MolfileCreator(mol);
                    String rawMolfile = creator.getMolfile();

                    // Посимвольно вычищаем неразрывные пробелы (NBSP / 160)
                    String[] lines = rawMolfile.split("\\r?\\n");
                    java.util.List<String> cleanLines = new java.util.ArrayList<>();

                    for (String line : lines) {
                        StringBuilder sb = new StringBuilder();
                        for (int i = 0; i < line.length(); i++) {
                            char c = line.charAt(i);
                            if (c == 160 || Character.isWhitespace(c)) {
                                sb.append(' '); // Строго ASCII-пробел
                            } else if (c == 8203) {
                                continue; // Нулевой пробел дропаем
                            } else {
                                sb.append(c);
                            }
                        }
                        cleanLines.add(sb.toString());
                    }

                    int countsLineIndex = -1;
                    for (int i = 0; i < cleanLines.size(); i++) {
                        if (cleanLines.get(i).contains("V2000")) {
                            countsLineIndex = i;
                            break;
                        }
                    }

                    StringBuilder validMolfile = new StringBuilder();
                    if (countsLineIndex != -1) {
                        // Гарантируем валидную структуру заголовка MDL V2000
                        validMolfile.append("Actelion Java MolfileCreator 1.0\n\n\n");
                        validMolfile.append(cleanLines.get(countsLineIndex)).append("\n");
                        for (int i = countsLineIndex + 1; i < cleanLines.size(); i++) {
                            validMolfile.append(cleanLines.get(i)).append("\n");
                        }
                    } else {
                        for (String line : cleanLines) {
                            validMolfile.append(line).append("\n");
                        }
                    }

                    cleanMolfile = validMolfile.toString();
                }
            }

            // 2. Тестируем боевую вставку/парсинг через правильный каст к cstring
            String insertTestSql = "SELECT public.mol_from_ctab(?::cstring);";

            try (PreparedStatement stmt = conn.prepareStatement(insertTestSql)) {
                stmt.setString(1, cleanMolfile);
                try (ResultSet rs = stmt.executeQuery()) {
                    if (rs.next()) {
                        Object res = rs.getObject(1);
                        System.out.println("-> Сast Result: " + (res != null ? "УСПЕШНО (Объект mol создан)" : "NULL"));
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}