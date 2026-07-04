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
        System.out.println("=== STARTING MOL_FILE AND MOL_FILE_RAW UPDATE ===");

        Properties props = new Properties();
        props.setProperty("user", USER);
        props.setProperty("password", PASSWORD);

        IDCodeParser parser = new IDCodeParser();

        String selectQuery = "SELECT id, idcode, id_coords_2d FROM public.book_base WHERE idcode IS NOT NULL AND mol_file_raw IS NULL;";
        String updateQuery = "UPDATE public.book_base SET mol_file = public.mol_from_ctab(?::cstring), mol_file_raw = ? WHERE id = ?;";

        try (Connection conn = DriverManager.getConnection(DB_URL, props);
             PreparedStatement selectStmt = conn.prepareStatement(selectQuery);
             PreparedStatement updateStmt = conn.prepareStatement(updateQuery);
             ResultSet rs = selectStmt.executeQuery()) {

            conn.setAutoCommit(false);

            int count = 0;
            int batchSize = 1000;

            while (rs.next()) {
                int id = rs.getInt("id");
                String idcode = rs.getString("idcode");
                String coords = rs.getString("id_coords_2d");

                if (idcode.trim().isEmpty()) continue;

                try {
                    StereoMolecule mol = new StereoMolecule();
                    parser.parse(mol, idcode, coords);
                    MolfileCreator creator = new MolfileCreator(mol);
                    String rawMolfile = creator.getMolfile();

                    // 1 — вставляем в mol_file (конвертируется картриджем)
                    updateStmt.setString(1, rawMolfile);
                    // 2 — сохраняем чистый текст с координатами в mol_file_raw
                    updateStmt.setString(2, rawMolfile);
                    // 3 — ID для WHERE
                    updateStmt.setInt(3, id);

                    updateStmt.addBatch();
                    count++;

                    if (count % batchSize == 0) {
                        updateStmt.executeBatch();
                        conn.commit();
                        System.out.println("Обновлено строк: " + count);
                    }

                } catch (Exception e) {
                    System.err.println("[SKIP] Ошибка генерации структуры для ID " + id + ": " + e.getMessage());
                }
            }

            if (count % batchSize != 0) {
                updateStmt.executeBatch();
                conn.commit();
            }

            System.out.println("\n=== ОБНОВЛЕНИЕ ЗАВЕРШЕНО! Заполнено строк: " + count + " ===");

        } catch (SQLException e) {
            System.err.println("\n[CRITICAL SQL ERROR] Сбой выполнения пакета. Откат изменений.");
            e.printStackTrace();

            SQLException nextEx = e.getNextException();
            while (nextEx != null) {
                System.err.println("Детали ошибки базы: " + nextEx.getMessage());
                nextEx = nextEx.getNextException();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}