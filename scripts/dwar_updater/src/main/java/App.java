import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Properties;

import com.actelion.research.chem.IDCodeParser;
import com.actelion.research.chem.StereoMolecule;
import com.actelion.research.chem.MolfileCreator;

public class App {

    static {
        java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"));
        System.setProperty("user.timezone", "UTC");
    }

    private static final String DB_URL = "jdbc:postgresql://localhost:5433/archive_db";
    private static final String USER = "chemist";
    private static final String PASSWORD = "archive_pass";

    public static void main(String[] args) {
        System.out.println("=== STARTING SAFE LINEAR RESTORATION ===");

        Properties props = new Properties();
        props.setProperty("user", USER);
        props.setProperty("password", PASSWORD);
        props.setProperty("options", "-c timezone=UTC");

        // Выбираем строго по возрастанию ID, которые больше предыдущего максимального
        String selectQuery = "SELECT id, idcode, id_coords_2d FROM book_base " +
                "WHERE id > ? AND idcode IS NOT NULL AND id_coords_2d IS NOT NULL " +
                "ORDER BY id ASC LIMIT ?;";

        String updateQuery = "UPDATE book_base SET mol_file = ?::mol WHERE id = ?;";

        int batchSize = 2500;
        long totalProcessed = 0;
        long lastId = -1; // Сюда пишем последний обработанный ID, чтобы двигаться строго вперед

        IDCodeParser parser = new IDCodeParser();

        try (Connection conn = DriverManager.getConnection(DB_URL, props);
             PreparedStatement selectStmt = conn.prepareStatement(selectQuery);
             PreparedStatement updateStmt = conn.prepareStatement(updateQuery)) {

            conn.setAutoCommit(false);

            boolean hasMore = true;
            while (hasMore) {
                selectStmt.setLong(1, lastId);
                selectStmt.setInt(2, batchSize);

                try (ResultSet rs = selectStmt.executeQuery()) {
                    int rowsInBatch = 0;
                    boolean foundAnyRows = false;

                    while (rs.next()) {
                        foundAnyRows = true;
                        long id = rs.getLong("id");
                        lastId = id; // Запоминаем самый большой ID в текущем батче

                        String idcode = rs.getString("idcode");
                        String idCoords2D = rs.getString("id_coords_2d");

                        if (idcode == null || idcode.isEmpty()) continue;

                        try {
                            StereoMolecule mol = new StereoMolecule();
                            parser.parse(mol, idcode, idCoords2D);

                            MolfileCreator creator = new MolfileCreator(mol);
                            String molfileContent = creator.getMolfile();

                            if (molfileContent == null || molfileContent.trim().isEmpty()) continue;

                            updateStmt.setString(1, molfileContent);
                            updateStmt.setLong(2, id);
                            updateStmt.addBatch();

                            rowsInBatch++;
                        } catch (Exception e) {
                            System.err.println("Error creating molfile for ID " + id + ": " + e.getMessage());
                        }
                    }

                    // Если ResultSet оказался абсолютно пустым — мы 100% дошли до конца таблицы
                    if (!foundAnyRows) {
                        System.out.println("[INFO] No more rows found in database. Finishing.");
                        hasMore = false;
                        break;
                    }

                    // Если в батче были валидные апдейты — выполняем
                    if (rowsInBatch > 0) {
                        updateStmt.executeBatch();
                        conn.commit();
                    } else {
                        conn.commit();
                    }

                    totalProcessed += rowsInBatch;
                    System.out.println("Processed up to ID: " + lastId + ". Total updated in this session: " + totalProcessed);

                } catch (Exception e) {
                    conn.rollback();
                    System.err.println("Batch failed at ID " + lastId + ", rolling back batch. Error: " + e.getMessage());
                    lastId++;
                }
            }

            System.out.println("\n--- Done! ---");
            System.out.println("Linear processing finished. Total attempted updates: " + totalProcessed);

        } catch (Exception e) {
            System.err.println("Database error occurred: " + e.getMessage());
            e.printStackTrace();
        }
    }
}